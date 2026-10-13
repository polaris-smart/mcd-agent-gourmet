"""A bounded set of complete meals, verified against live menu/detail/price."""

import csv
import copy
import re
from datetime import datetime, timezone
from .mcp import MCPError
from .catalog import FRIES_CODES, DRINK_SUGAR, SIDE_CODES, DRINK_CODES, MAIN_SPICY
from itertools import product
from .customize import modifications
from .channels import order_context


def nutrition_rows(value):
    if isinstance(value, str):
        lines = value.strip().splitlines()
        match = re.fullmatch(r"\[\d+\]\{([^}]+)\}:", lines[0]) if lines else None
        if not match:
            raise MCPError("无法识别官方营养表格式。")
        keys = match.group(1).split(",")
        rows = []
        for line in lines[1:]:
            values = next(csv.reader([line.strip()]))
            if len(values) != len(keys):
                raise MCPError("营养表列数变化，停止解析。")
            rows.append(dict(zip(keys, values)))
    elif isinstance(value, list):
        rows = value
    else:
        raise MCPError("无法识别营养表数据类型。")
    result = {}
    for row in rows:
        name = row.get("productName")
        nutrients = {}
        for source, target in (("energyKcal", "energy_kcal"), ("sodium", "sodium_mg"), ("protein", "protein_g")):
            raw = row.get(source)
            nutrients[target] = float(raw) if raw not in (None, "null", "") else None
        if name in result and result[name] != nutrients:
            result[name] = {k: None for k in nutrients}
        else:
            result[name] = nutrients
    return result


def assemble(detail, replacements, ice='any', omit=()):
    rounds, items = [], []
    groups = detail.get("rounds", [])
    if len(groups) != 3:
        raise MCPError("当前模板只支持已核对的三轮套餐，不能猜测套餐组成。")
    for group, kind in zip(groups, ("main", "side", "drink")):
        code = replacements.get(str(group["id"]))
        choices = [x for x in group["choices"] if x["code"] == code] if code else [x for x in group["choices"] if x.get("isDefault") and x.get("quantity", 0) > 0]
        if len(choices) != 1 or group.get("minQuantity") != 1 or group.get("maxQuantity") != 1:
            raise MCPError("套餐选项已变化；请重新检查餐单模板。")
        choice = choices[0]
        known_codes = {'main': set(MAIN_SPICY), 'side': set(SIDE_CODES), 'drink': set(DRINK_CODES)}
        if choice['code'] not in known_codes[kind]:
            raise MCPError('所选餐品分类尚未核对，不能仅凭轮次猜它是主食、小食或饮料。')
        modification, labels = modifications(choice, ice if kind == 'drink' else 'any', omit if kind == 'main' else ())
        request_choice = {"code":choice["code"], "quantity":1}
        if modification:
            request_choice['modification'] = modification
        rounds.append({"round": str(group["id"]), "comboItemList": [request_choice]})
        items.append({"code": choice["code"], "name": choice["name"], "quantity": 1,
                      "kind": kind, "customizations": labels,
                      "ice": ice if kind == 'drink' and ice != 'any' else None,
                      "nutrition_customized": bool(omit and kind == 'main'), "is_fries": kind == "side" and choice["code"] in FRIES_CODES,
                      "sugar": DRINK_SUGAR.get(choice["code"]) if kind == "drink" else None})
    return {"productCode": detail["code"], "quantity": 1, "roundList": rounds}, items


def quoted_cents(value):
    price = value.get("price") if isinstance(value, dict) else None
    if type(price) is not int or price < 0:
        raise MCPError("官方核价缺少整数分 price 字段；不使用菜单展示价替代。")
    return price


def store_coupons(client, plan):
    value = client.call('query-store-coupons', order_context(plan))
    if not isinstance(value, list) or not all(isinstance(c, dict) for c in value):
        raise MCPError('无法识别当前门店可用券结构。')
    return value


def coupon_choices(coupons, plan):
    """Only titles and matching candidate IDs leave the private response."""
    result = []
    for coupon in coupons:
        products = {p.get('productCode') for p in coupon.get('products', []) if isinstance(p, dict)}
        result.append({'title': coupon.get('title', '未命名券'),
                       'candidate_ids': [p['id'] for p in plan['candidates'] if p['product_code'] in products]})
    return result


def plan_with_coupon(plan, coupons, title, candidate_id):
    matches = [c for c in coupons if c.get('title') == title]
    if len(matches) != 1:
        raise ValueError('券名称未找到或不唯一，请重新查询可用券；不能猜测券标识。')
    coupon = matches[0]
    adjusted = copy.deepcopy(plan)
    spec = next((p for p in adjusted['candidates'] if p['id'] == candidate_id), None)
    if spec is None:
        raise ValueError('候选 ID 不存在。')
    products = {p.get('productCode') for p in coupon.get('products', []) if isinstance(p, dict)}
    if spec['product_code'] not in products:
        raise ValueError('该券的商品与这份套餐不匹配；不会把单品券强行套用到套餐。')
    pair = {k: coupon.get(k) for k in ('couponId', 'couponCode')}
    if not all(isinstance(v, str) and v for v in pair.values()):
        raise MCPError('可用券缺少成对标识，停止用券核价。')
    spec['coupon'] = pair
    return adjusted


def fetch_snapshot(client, plan, on_progress=None, coupon_title=None, coupon_candidate=None, expand=False, ice='any', omit=()):
    if bool(coupon_title) != bool(coupon_candidate):
        raise ValueError('用券须同时指定券名称和候选 ID。')
    if expand and coupon_title:
        raise ValueError("扩展组合与单候选用券请分轮核价，避免把券套到未确认的组合。")
    if coupon_title:
        plan = plan_with_coupon(plan, store_coupons(client, plan), coupon_title, coupon_candidate)
    store, specs = plan["store"], plan["candidates"]
    if not 1 <= len(specs) <= 12:
        raise ValueError("一次最多核价 12 份餐单。")
    if not isinstance(store.get("code"), str) or not store["code"].isdigit():
        raise ValueError("门店编码必须是数字字符串。")
    base = order_context(plan)
    menu = client.call("query-meals", base)
    nutrition = nutrition_rows(client.call("list-nutrition-foods", {}))
    details, results = {}, []
    if expand:
        expanded = []
        for code in dict.fromkeys(s['product_code'] for s in specs):
            if code not in menu.get('meals', {}):
                raise MCPError('当前门店没有候选套餐，请选择其他菜单。')
            detail = client.call('query-meal-detail', dict(base, code=code))
            details[code] = detail
            groups = detail.get('rounds', [])
            if len(groups) != 3:
                raise MCPError('套餐轮次已变化，停止扩展。')
            sides = [c for c in groups[1]['choices'] if c['code'] in SIDE_CODES]
            drinks = [c for c in groups[2]['choices'] if c['code'] in DRINK_CODES]
            source = next(s for s in specs if s['product_code'] == code)
            if source.get('coupon'):
                raise ValueError('扩展组合不自动继承优惠券。')
            if not sides or not drinks:
                raise MCPError('当前门店缺少可识别的小食或饮料选项。')
            for side, drink in product(sides, drinks):
                expanded.append({'id': f"{code}-{side['code']}-{drink['code']}",
                    'product_code':code, 'label':side['name']+' · '+drink['name'],
                    'spicy':source.get('spicy'), 'replacements':{
                        str(groups[1]['id']):side['code'], str(groups[2]['id']):drink['code']}})
        if len(expanded) > 12:
            raise ValueError('扩展后超过 12 份，请缩小套餐范围；未截断候选。')
        specs = expanded
    for spec in specs:
        code = spec["product_code"]
        if code not in menu.get("meals", {}):
            raise MCPError("当前门店没有候选套餐；请重新选餐，不沿用旧数据。")
        if code not in details:
            details[code] = client.call("query-meal-detail", dict(base, code=code))
        request_item, items = assemble(details[code], spec.get("replacements", {}), ice=ice, omit=omit)
        coupon = spec.get("coupon")
        if coupon is not None:
            if not isinstance(coupon, dict) or set(coupon) != {"couponId", "couponCode"} or not all(isinstance(v, str) and v for v in coupon.values()):
                raise ValueError("优惠券必须同时提供有效 couponId 与 couponCode。")
            request_item.update(coupon)
        quote = client.call("calculate-price", dict(base, items=[request_item]))
        price = quoted_cents(quote)
        totals = {}
        missing = [i["name"] for i in items if i["name"] not in nutrition or i.get("nutrition_customized")]
        for key in ("energy_kcal", "sodium_mg", "protein_g"):
            values = [None if i.get("nutrition_customized") else nutrition.get(i["name"], {}).get(key) for i in items]
            totals[key] = None if any(v is None for v in values) else sum(values)
        result = {"id": spec["id"], "name": details[code]["name"], "variant": spec["label"],
                  "store_code": store["code"], "items": items, "price_cents": price,
                  "spicy": spec.get("spicy") if spec.get("spicy") is not None else MAIN_SPICY.get(items[0]["code"]), "nutrition_missing": missing,
                  "coupon_requested": coupon is not None,
                  "take_way_options": [{k:v.get(k) for k in ('code','title','subtitle')} for v in quote.get('takeWayList', [])],
                  "fees_cents": {k:quote.get(k) for k in ('deliveryPrice','packingPrice','tablewarePrice')},
                  "coupon_applied": None if coupon else False, "quote_tool": "calculate-price", **totals}
        results.append(result)
        if on_progress:
            on_progress(result)
    return {"mode": "live", "fulfillment": {"channel": plan.get("fulfillment", {}).get("channel", "pickup")}, "store": store, "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "麦当劳官方 MCP：calculate-price + list-nutrition-foods",
            "scope": "仅比较本轮候选；不保证全菜单最低价；营养为标准份量的单品加总。", "plans": results}
