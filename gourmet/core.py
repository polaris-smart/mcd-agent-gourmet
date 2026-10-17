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


def _money(cents):
    return '¥%.2f' % (cents / 100)


def _mg(value):
    return '%g mg' % value


def _dominates(better, worse, dimensions):
    a, b = dimensions(better), dimensions(worse)
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def _explain(strategy, better, worse):
    """把"被谁支配"翻译成可读理由；不编造评分。"""
    why = []
    if strategy == 'price_sodium':
        if better['price_cents'] < worse['price_cents']:
            why.append('价格更低（%s vs %s）' % (_money(better['price_cents']), _money(worse['price_cents'])))
        if better['sodium_mg'] < worse['sodium_mg']:
            why.append('钠更低（%s vs %s）' % (_mg(better['sodium_mg']), _mg(worse['sodium_mg'])))
        return why
    if strategy == 'taste_sodium':
        if not better['taste_match'] and worse['taste_match']:
            why.append('更贴近你选的口味')
        if better['sodium_mg'] < worse['sodium_mg']:
            why.append('钠更低（%s vs %s）' % (_mg(better['sodium_mg']), _mg(worse['sodium_mg'])))
        return why
    axes = (('price_cents', '价格', _money, True), ('sodium_mg', '钠', _mg, True),
            ('energy_kcal', '能量', lambda v: '%g kcal' % v, True),
            ('protein_g', '蛋白质', lambda v: '%g g' % v, False))
    for key, label, fmt, lower_is_better in axes:
        a, b = better.get(key), worse.get(key)
        if a is None or b is None:
            continue
        if (a < b) if lower_is_better else (a > b):
            why.append('%s更%s（%s vs %s）' % (label, '低' if lower_is_better else '高', fmt(a), fmt(b)))
    return why


def _pareto(pool, strategy, dimensions, order):
    """非支配前沿。同值并列保留；被支配者给出代表支配者与理由。"""
    frontier, dominated = [], {}
    for plan in sorted(pool, key=order):
        beaters = [q for q in pool if q['id'] != plan['id'] and _dominates(q, plan, dimensions)]
        if beaters:
            representative = sorted(beaters, key=order)[0]
            dominated[plan['id']] = {'by': representative['id'],
                                     'why': _explain(strategy, representative, plan)}
        else:
            frontier.append(plan['id'])
    return frontier, dominated


def _strategy_pools(plans):
    known = [p for p in plans if p['eligible'] and p.get('sodium_mg') is not None]
    complete = [p for p in known if p.get('energy_kcal') is not None and p.get('protein_g') is not None]
    return {
        'price_sodium': (known, lambda p: (p['price_cents'], p['sodium_mg']),
                         lambda p: (p['price_cents'], p['id'])),
        'taste_sodium': (known, lambda p: (int(not p['taste_match']), p['sodium_mg']),
                         lambda p: (p['price_cents'], p['id'])),
        'nutrition_multi': (complete,
                            lambda p: (p['price_cents'], p['sodium_mg'], p['energy_kcal'], -p['protein_g']),
                            lambda p: (p['price_cents'], p['id'])),
    }


def tradeoff_candidates(plans):
    """Non-dominated known candidates, without a made-up health score."""
    result = {}
    for name, (pool, dimensions, order) in _strategy_pools(plans).items():
        frontier, _ = _pareto(pool, name, dimensions, order)
        result[name] = frontier
    return result


def tradeoff_reasons(plans):
    """每个比较角度：谁在前沿、谁被谁支配、以及因数据不完整而未进入的原因。"""
    result = {}
    for name, (pool, dimensions, order) in _strategy_pools(plans).items():
        frontier, dominated = _pareto(pool, name, dimensions, order)
        in_pool = {p['id'] for p in pool}
        result[name] = {
            'frontier': frontier,
            'dominated': dominated,
            'excluded_incomplete': sorted(p['id'] for p in plans
                                          if p['eligible'] and p['id'] not in in_pool),
        }
    return result


def budget_ladder(plans, budget_cents, max_steps=3):
    """当前预算无解时的可行域阶梯：预算提到多少、能有几份可选。

    只描述"提高预算"这一个变量；不放宽口味、小食、饮料或营养条件。
    """
    if budget_cents is None or any(p['eligible'] for p in plans):
        return {'needed_cents': None, 'steps': []}
    only_budget = [p for p in plans if p['reasons'] and all(r.startswith('超预算') for r in p['reasons'])]
    if not only_budget:
        return {'needed_cents': None, 'steps': []}
    prices = sorted({p['price_cents'] for p in only_budget})
    steps = []
    for price in prices[:max_steps]:
        steps.append({'budget_cents': price,
                      'candidates': sum(1 for p in only_budget if p['price_cents'] <= price),
                      'increase_cents': price - budget_cents})
    return {'needed_cents': prices[0], 'steps': steps}


def data_notice(data):
    if data['mode'] == 'live':
        return '本轮官方实时核价；价格与供应仍须以官方购买渠道确认。'
    if data['mode'] == 'synthetic':
        return '合成测试数据，不是官方报价，不可用于购买。'
    return '历史快照演示，不是当前实时价格；使用 --live 重新核价。'


def default_pick(result):
    """默认答案：不需要用户从多份里挑的那一份。

    有基线时选"省得最多"的；否则选符合条件的候选里价格最低的。
    """
    eligible = [p for p in result["plans"] if p["eligible"]]
    if not eligible:
        return None
    if result.get("baseline"):
        return sorted(eligible, key=lambda p: (-p.get("saving_cents", 0), p["price_cents"], p["id"]))[0]
    return sorted(eligible, key=lambda p: (p["price_cents"], p["id"]))[0]


def pick_reason(result, plan_id):
    """一句**可核对**的理由（不是说服文案）：只在事实成立时这么说。"""
    plan = next((p for p in result["plans"] if p["id"] == plan_id), None)
    if plan is None or not plan["eligible"]:
        raise ValueError("只能为符合条件的候选给理由。")
    eligible = [p for p in result["plans"] if p["eligible"]]
    baseline = result.get("baseline")
    if baseline and plan.get("saving_cents", 0) > 0:
        return "比「%s」省 ¥%.2f（%.1f%%）" % (baseline["label"], plan["saving_cents"] / 100, plan["saving_percent"])
    cheapest = sorted(eligible, key=lambda p: (p["price_cents"], p["id"]))[0]
    if cheapest["id"] == plan["id"]:
        return "在满足条件的 %d 份候选里价格最低（¥%.2f）" % (len(eligible), plan["price_cents"] / 100)
    known = [p for p in eligible if p.get("sodium_mg") is not None]
    if known:
        lowest = sorted(known, key=lambda p: (p["sodium_mg"], p["price_cents"], p["id"]))[0]
        if lowest["id"] == plan["id"]:
            return "在钠数据完整的候选里钠最低（%g mg）" % plan["sodium_mg"]
    return "符合你的全部硬性条件"


def order_card(result, plan_id=None):
    """可复制的点单卡：门店、取餐方式、每样官方名称、合计。

    只记录"选哪一份"，不创建订单、不支付。
    """
    target = plan_id
    if target is None:
        picked = default_pick(result)
        if picked is None:
            raise ValueError("没有符合条件的候选，无法生成点单卡。")
        target = picked["id"]
    plan = next((p for p in result["plans"] if p["id"] == target), None)
    if plan is None:
        raise ValueError("候选 ID 不存在。")
    if not plan["eligible"]:
        raise ValueError("该候选不符合当前条件，不能生成点单卡。")
    ways = plan.get("take_way_options") or []
    way = ways[0].get("title") if ways and isinstance(ways[0], dict) else "到店自取"
    lines = ["门店：%s（%s）· %s" % (result["store"]["name"], result["store"]["code"], way)]
    for index, item in enumerate(plan["items"], 1):
        spec = "、".join(item.get("customizations") or [])
        lines.append("%d. %s%s" % (index, item["name"], ("（%s）" % spec) if spec else ""))
    lines.append("合计：¥%.2f" % (plan["price_cents"] / 100))
    if result.get("baseline") and plan.get("saving_cents", 0) > 0:
        lines.append("比「%s」省 ¥%.2f（%.1f%%）"
                     % (result["baseline"]["label"], plan["saving_cents"] / 100, plan["saving_percent"]))
    if result["requirements"]["people"] > 1:
        lines.append("%d 人；人均 ¥%.2f" % (result["requirements"]["people"], plan["per_person_cents"] / 100))
    if plan.get("display_price_note"):
        lines.append("价格说明：%s" % plan["display_price_note"])
    lines.append("以上只是记录你的选择；没有下单、没有支付。")
    return {"plan_id": plan["id"], "title": plan["name"], "variant": plan["variant"],
            "lines": lines, "text": "\n".join(lines), "total_cents": plan["price_cents"],
            "status": "selected_not_ordered"}


def _resolve_baseline(data, plans, plan_id, cents, label, store_code):
    """解析省钱数字的基线。来源不明或跨店一律拒绝——省钱数字必须可复算。"""
    if plan_id is not None and cents is not None:
        raise ValueError("基线只能给一种：候选 ID 或明确报价。")
    if plan_id is not None:
        source = next((p for p in plans if p["id"] == plan_id), None)
        if source is None:
            raise ValueError("基线候选不在本店候选中。")
        return {"kind": "plan", "plan_id": plan_id, "price_cents": source["price_cents"],
                "label": label or source["name"], "store_code": data["store"]["code"]}
    if cents is not None:
        if type(cents) is not int or cents <= 0:
            raise ValueError("基线报价须为正整数分。")
        if store_code != data["store"]["code"]:
            raise ValueError("基线必须来自同一门店；不能拿别家店的价格比。")
        return {"kind": "quote", "plan_id": None, "price_cents": cents,
                "label": label or "外部基线报价", "store_code": store_code}
    if label is not None or store_code is not None:
        raise ValueError("给了基线说明却没有基线价格。")
    return None


def review(data, budget_cents=3500, taste="any", sodium_limit=None, side="any", now=None,
           sugar="any", energy_limit=None, protein_min=None, freshness_minutes=15, ice="any",
           people=1, budget_scope="total",
           baseline_plan_id=None, baseline_cents=None, baseline_label=None, baseline_store_code=None):
    """按用户约束审阅候选餐单。

    people        就餐人数（1～8）：主食与饮料各 ≥ people、小食 ≥ 1。
    budget_scope  'total'＝budget_cents 为整单预算；'per_person'＝为人均预算。
    baseline_*    省钱数字的基线（"你本来会怎么点"）。两种给法二选一：
                  · baseline_plan_id：本店候选中的某一份（推荐，天然同店同模式）
                  · baseline_cents + baseline_store_code：外部真实核价（必须同店，避免跨店比较）
    """
    validate_snapshot(data)
    if budget_cents is not None and (type(budget_cents) is not int or not 0 < budget_cents <= 1_000_000):
        raise ValueError("预算无效；不设预算请显式传 None。")
    if type(people) is not int or not 1 <= people <= 8:
        raise ValueError("就餐人数须为 1～8 的整数。")
    if budget_scope not in ("total", "per_person"):
        raise ValueError("预算口径须为整单（total）或人均（per_person）。")
    if budget_cents is None and budget_scope == "per_person":
        raise ValueError("不设预算时不能再指定人均口径。")
    effective_budget = None if budget_cents is None else (budget_cents * people if budget_scope == "per_person" else budget_cents)
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
        need = {"main": people, "drink": people, "side": 1}
        if any(counts[k] < need[k] for k in need):
            if people == 1:
                reasons.append("不满足主食＋小食＋饮料各至少一份")
            else:
                reasons.append("不满足 %d 人份（主食 %d/%d、饮料 %d/%d、小食 %d/%d）"
                               % (people, counts["main"], need["main"], counts["drink"], need["drink"],
                                  counts["side"], need["side"]))
        if effective_budget is not None and p["price_cents"] > effective_budget:
            reasons.append("超预算 ¥%.2f" % ((p["price_cents"] - effective_budget) / 100))
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
                 remaining_cents=None if effective_budget is None else effective_budget - p["price_cents"],
                 per_person_cents=(p["price_cents"] + people - 1) // people,
                 structure=("single" if counts["main"] <= 1 and counts["drink"] <= 1 else "share"),
                 taste_match=(taste != "spicy" or p.get("spicy") is True))
        plans.append(p)
    eligible = [p for p in plans if p["eligible"]]
    baseline = _resolve_baseline(data, plans, baseline_plan_id, baseline_cents, baseline_label, baseline_store_code)
    if baseline:
        for p in plans:
            p["saving_cents"] = baseline["price_cents"] - p["price_cents"]
            p["saving_percent"] = round(100.0 * p["saving_cents"] / baseline["price_cents"], 1)
    best_saving = None
    if baseline:
        winners = [p for p in eligible if p["saving_cents"] > 0]
        if winners:
            pick = sorted(winners, key=lambda p: (-p["saving_cents"], p["price_cents"], p["id"]))[0]
            best_saving = {"plan_id": pick["id"], "saving_cents": pick["saving_cents"],
                           "saving_percent": pick["saving_percent"]}
    budget_pick = min(eligible, key=lambda p: (p["price_cents"], p["id"]), default=None)
    known = [p for p in eligible if p.get("sodium_mg") is not None]
    nutrition_pick = min(known, key=lambda p: (p["sodium_mg"], p["price_cents"], p["id"]), default=None)
    taste_pick = min(eligible, key=lambda p: (not p["taste_match"], p["price_cents"], p["id"]), default=None)
    choices = {"budget": budget_pick, "nutrition": nutrition_pick, "taste": taste_pick}
    reviewers = {role: p["id"] if p else None for role, p in choices.items()}
    result = {"fulfillment": data.get("fulfillment", {"channel":"pickup"}), "mode": data["mode"], "store": data["store"], "captured_at": data["captured_at"],
              "data_notice": data_notice(data),
              "requirements": {"budget_cents": budget_cents, "budget_scope": budget_scope,
                               "effective_budget_cents": effective_budget, "budget_unspecified": budget_cents is None,
                               "people": people,
                               "taste": taste, "sodium_limit": sodium_limit, "side": side, "sugar": sugar,
                               "energy_limit": energy_limit, "protein_min": protein_min, "freshness_minutes": freshness_minutes, "ice": ice},
              "plans": plans, "reviewers": reviewers, "feasible_count": len(eligible),
              "disagreement": len({x for x in reviewers.values() if x}) > 1, "selected": None,
              "baseline": baseline, "best_saving": best_saving}
    result['tradeoffs'] = tradeoff_candidates(plans)
    result['tradeoff_reasons'] = tradeoff_reasons(plans)
    result['budget_ladder'] = budget_ladder(plans, effective_budget)
    enough = [p for p in plans if all(r.startswith('超预算') for r in p['reasons'])]
    result['next_step'] = ('未设预算：以上候选都符合其他硬性条件，请比较后选择。' if eligible and effective_budget is None else
        '可选餐单均已列出，请比较后选择。' if eligible else
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
