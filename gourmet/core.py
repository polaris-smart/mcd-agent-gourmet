"""Deterministic reviewers: complete meals first, then explicit trade-offs."""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def money_to_cents(value):
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("预算必须是有效金额。") from None
    if not amount.is_finite() or amount <= 0 or amount > 10000 or amount * 100 != (amount * 100).to_integral_value():
        raise ValueError("预算须大于 0、不超过 10000 元，最多两位小数。")
    return int(amount * 100)


def validate_snapshot(data):
    if data.get("mode") not in ("snapshot", "live", "synthetic"):
        raise ValueError("必须明确数据来源模式。")
    if not isinstance(data.get("store", {}).get("code"), str) or not data.get("captured_at"):
        raise ValueError("缺少门店或核价时间。")
    ids = set()
    if not isinstance(data.get("plans"), list) or not data["plans"]:
        raise ValueError("没有候选餐单。")
    for p in data["plans"]:
        if not isinstance(p.get("id"), str) or p["id"] in ids:
            raise ValueError("餐单 ID 缺失或重复。")
        ids.add(p["id"])
        if type(p.get("price_cents")) is not int or p["price_cents"] < 0:
            raise ValueError("整单价格必须是非负整数分。")
        if p.get("store_code") != data["store"]["code"]:
            raise ValueError("不能混用不同门店的报价。")
        if not isinstance(p.get("items"), list) or not p["items"]:
            raise ValueError("餐单缺少明细。")
        for item in p["items"]:
            if type(item.get("quantity")) is not int or item["quantity"] < 1:
                raise ValueError("餐品份数必须是正整数。")
            if item.get("kind") not in ("main", "side", "drink"):
                raise ValueError("未知餐品类别。")
        for key in ("energy_kcal", "sodium_mg", "protein_g"):
            value = p.get(key)
            if value is not None and (type(value) not in (int, float) or value < 0 or value != value or value == float("inf")):
                raise ValueError("营养值必须非负，缺失用 null。")
    return data


def tradeoff_candidates(plans):
    """Non-dominated known candidates, without a made-up health score."""
    known = [p for p in plans if p['eligible'] and p.get('sodium_mg') is not None]
    strategies = {
        'price_sodium': lambda p: (p['price_cents'], p['sodium_mg']),
        'taste_sodium': lambda p: (int(not p['taste_match']), p['sodium_mg']),
    }
    result = {}
    for name, dimensions in strategies.items():
        def dominated(p):
            a = dimensions(p)
            return any(all(x <= y for x, y in zip(dimensions(q), a)) and
                       any(x < y for x, y in zip(dimensions(q), a)) for q in known)
        result[name] = [p['id'] for p in sorted(known, key=lambda p: (p['price_cents'], p['id']))
                        if not dominated(p)]
    complete = [p for p in known if p.get('energy_kcal') is not None and p.get('protein_g') is not None]
    def dims(p):
        return (p['price_cents'], p['sodium_mg'], p['energy_kcal'], -p['protein_g'])
    result['nutrition_multi'] = [p['id'] for p in sorted(complete, key=lambda p: (p['price_cents'], p['id']))
        if not any(all(x <= y for x, y in zip(dims(q), dims(p))) and
                   any(x < y for x, y in zip(dims(q), dims(p))) for q in complete)]
    return result


def data_notice(data):
    if data['mode'] == 'live':
        return '本轮官方实时核价；价格与供应仍须以官方购买渠道确认。'
    if data['mode'] == 'synthetic':
        return '合成测试数据，不是官方报价，不可用于购买。'
    return '历史快照演示，不是当前实时价格；使用 --live 重新核价。'


def review(data, budget_cents=3500, taste="any", sodium_limit=None, side="any", now=None,
           sugar="any", energy_limit=None, protein_min=None, freshness_minutes=15, ice="any"):
    validate_snapshot(data)
    if type(budget_cents) is not int or not 0 < budget_cents <= 1_000_000:
        raise ValueError("预算无效。")
    if taste not in ("any", "spicy", "no-spicy") or side not in ("any", "fries"):
        raise ValueError("未知偏好。")
    if sodium_limit is not None and (type(sodium_limit) is not int or sodium_limit <= 0):
        raise ValueError("钠上限须为正整数 mg。")
    if ice not in ('any','standard','less','none','extra'):
        raise ValueError('未知冰量。')
    if sugar not in ('any', 'regular', 'zero'):
        raise ValueError('未知饮料偏好。')
    for value in (energy_limit, protein_min):
        if value is not None and (type(value) is not int or value <= 0):
            raise ValueError('能量上限、蛋白质下限须为正整数。')
    if type(freshness_minutes) is not int or not 1 <= freshness_minutes <= 60:
        raise ValueError('复核窗口须为 1～60 分钟。')
    stale = False
    if data["mode"] == "live":
        stamp = datetime.fromisoformat(data["captured_at"])
        if stamp.tzinfo is None:
            raise ValueError("核价时间必须包含时区。")
        age = ((now or datetime.now(timezone.utc)) - stamp).total_seconds()
        stale = age > freshness_minutes * 60 or age < -60
    plans = []
    for original in data["plans"]:
        p = dict(original)
        reasons = []
        counts = {kind: sum(i["quantity"] for i in p["items"] if i["kind"] == kind)
                  for kind in ("main", "side", "drink")}
        if any(counts[k] < 1 for k in counts):
            reasons.append("不满足主食＋小食＋饮料各至少一份")
        if p["price_cents"] > budget_cents:
            reasons.append("超预算 ¥%.2f" % ((p["price_cents"] - budget_cents) / 100))
        if taste == "no-spicy" and p.get("spicy") is not False:
            reasons.append("含辣或辣味信息未确认")
        if side == "fries" and not any(i.get("is_fries") for i in p["items"] if i["kind"] == "side"):
            reasons.append("小食不含薯条")
        if ice != 'any' and any(i.get('ice') != ice for i in p['items'] if i['kind'] == 'drink'):
            reasons.append('冰量未核验为所选条件；请实时特调核价')
        if sugar != 'any' and any(i.get('sugar') != sugar for i in p['items'] if i['kind'] == 'drink'):
            reasons.append('饮料含糖类型不符或未确认')
        for key, threshold, label, upper in (('energy_kcal', energy_limit, '能量', True), ('protein_g', protein_min, '蛋白质', False)):
            if threshold is not None:
                if p.get(key) is None:
                    reasons.append(label + '数据不完整，无法核验条件')
                elif (p[key] > threshold if upper else p[key] < threshold):
                    reasons.append('超过你设定的能量上限 %s kcal' % threshold if upper else '低于你设定的蛋白质下限 %s g' % threshold)
        if sodium_limit is not None:
            if p.get("sodium_mg") is None:
                reasons.append("钠数据不完整，无法核验上限")
            elif p["sodium_mg"] > sodium_limit:
                reasons.append("超过你设定的钠上限 %s mg" % sodium_limit)
        if stale:
            reasons.append("报价已过本工具 %s 分钟复核窗口，请重新核价" % freshness_minutes)
        p.update(eligible=not reasons, reasons=reasons,
                 remaining_cents=budget_cents - p["price_cents"],
                 taste_match=(taste != "spicy" or p.get("spicy") is True))
        plans.append(p)
    eligible = [p for p in plans if p["eligible"]]
    budget_pick = min(eligible, key=lambda p: (p["price_cents"], p["id"]), default=None)
    known = [p for p in eligible if p.get("sodium_mg") is not None]
    nutrition_pick = min(known, key=lambda p: (p["sodium_mg"], p["price_cents"], p["id"]), default=None)
    taste_pick = min(eligible, key=lambda p: (not p["taste_match"], p["price_cents"], p["id"]), default=None)
    choices = {"budget": budget_pick, "nutrition": nutrition_pick, "taste": taste_pick}
    reviewers = {role: p["id"] if p else None for role, p in choices.items()}
    result = {"fulfillment": data.get("fulfillment", {"channel":"pickup"}), "mode": data["mode"], "store": data["store"], "captured_at": data["captured_at"],
              "data_notice": data_notice(data),
              "requirements": {"budget_cents": budget_cents, "taste": taste, "sodium_limit": sodium_limit, "side": side, "sugar": sugar,
                               "energy_limit": energy_limit, "protein_min": protein_min, "freshness_minutes": freshness_minutes, "ice": ice},
              "plans": plans, "reviewers": reviewers, "feasible_count": len(eligible),
              "disagreement": len({x for x in reviewers.values() if x}) > 1, "selected": None}
    result['tradeoffs'] = tradeoff_candidates(plans)
    enough = [p for p in plans if all(r.startswith('超预算') for r in p['reasons'])]
    result['next_step'] = ('可选餐单均已列出，请比较后选择。' if eligible else
        '保持其他条件不变，候选中最低需要 ¥%.2f；是否增加预算由你决定。' % (min(p['price_cents'] for p in enough)/100) if enough else
        '当前候选没有满足其他条件的餐单。可在所选门店扩展组合，或由你修改偏好；不会自动放宽条件。')
    result["review_id"] = hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    return result


def select_plan(result, plan_id, review_id):
    if result["review_id"] != review_id:
        raise ValueError("条件已改变，请重新查看餐单。")
    plan = next((p for p in result["plans"] if p["id"] == plan_id and p["eligible"]), None)
    if plan is None:
        raise ValueError("该餐单不满足当前条件，不能确认。")
    return {"plan_id": plan_id, "review_id": review_id, "status": "selected_not_ordered",
            "price_cents": plan["price_cents"], "mode": result["mode"]}
