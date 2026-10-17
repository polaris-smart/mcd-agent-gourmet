"""A bounded set of complete meals, verified against live menu/detail/price."""

import csv
import copy
import json
import re
from datetime import datetime, timezone
from .mcp import MCPError
from .catalog import FRIES_CODES, DRINK_SUGAR, SIDE_CODES, DRINK_CODES, MAIN_SPICY
from itertools import product
from .customize import modifications
from .channels import order_context


DISPLAY_PRICE_CONDITIONS = {
    "早餐卡优惠": "需早餐卡权益",
    "促销优惠": "促销价（是否可用以官方当次核价为准）",
    "麦金卡优惠": "需麦金卡权益",
    "随单购早餐卡优惠": "需随单购买早餐卡",
    "随单购麦金卡优惠": "需随单购买麦金卡",
}


def price_text_to_cents(value):
    """菜单展示价是「元」字符串；解析不了就返回 None——不猜、不四舍五入。"""
    if not isinstance(value, str):
        return None
    text = value.strip().replace("¥", "").replace("￥", "").replace(",", "")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", text):
        return None
    whole, _, frac = text.partition(".")
    return int(whole) * 100 + int((frac + "00")[:2])


def display_price_report(item, quoted):
    """菜单展示价 + 它的适用条件。

    展示价**永远不是价格依据**：只要 discountType 等字段说明该价附带条件，
    就必须把条件说出来，并显式与 calculate-price 的核价并列。
    """
    item = item or {}
    cents = price_text_to_cents(item.get("currentPrice"))
    condition = DISPLAY_PRICE_CONDITIONS.get(item.get("discountType"))
    if condition is None and item.get("canWithOrder"):
        condition = "可随单购买卡；该价可能依赖随单购"
    note = None
    if cents is not None and condition and cents < quoted:
        note = ("菜单展示价 ¥%.2f 附带条件「%s」；实际核价 ¥%.2f——差额来自该条件未生效，"
                "只有核价才是你要付的钱。" % (cents / 100, condition, quoted / 100))
    elif cents is not None and condition:
        note = "菜单展示价 ¥%.2f 附带条件「%s」；以核价 ¥%.2f 为准。" % (cents / 100, condition, quoted / 100)
    elif cents is not None and cents != quoted:
        note = "菜单展示价 ¥%.2f 与核价 ¥%.2f 不一致，以核价为准。" % (cents / 100, quoted / 100)
    return {"display_price_cents": cents, "display_price_condition": condition, "display_price_note": note}


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


def tool_payload(result):
    """把 MCP result 解成工具的业务数据：优先 structuredContent，其次解析说明文里的原始 JSON。

    官方多数工具返回「说明文 + Original Response」，另一些直接给 structuredContent——两种都要能吃。
    """
    if not isinstance(result, dict):
        return None
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and structured:
        return structured
    text = "".join(part.get("text", "") for part in (result.get("content") or []) if isinstance(part, dict))
    if not text:
        return None
    marker = text.find("## Original Response")
    start = text.find("{", marker if marker >= 0 else 0)
    if start < 0:
        return None
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:index + 1])
                except ValueError:
                    return None
    return None


def order_history(result):
    """解析 order-list 返回的历史订单，新的在前。字段缺失不猜，缺门店或缺商品的订单不进结果。"""
    payload = None
    if isinstance(result, dict):
        if isinstance(result.get("data"), dict):
            payload = result                       # 标准业务包：{"data": {...}}
        elif isinstance(result.get("list"), list):
            payload = {"data": {"list": result["list"]}}   # 实测：order-list 直接返回 {"list": [...]}
        else:
            payload = tool_payload(result)         # 说明文 + Original Response / structuredContent
    orders = ((payload or {}).get("data") or {}).get("list") or []
    parsed = []
    for order in orders:
        if not isinstance(order, dict):
            continue
        products = []
        for item in order.get("orderProductList") or []:
            if not isinstance(item, dict):
                continue
            code = item.get("productCode")
            if not isinstance(code, str) or not code:
                continue
            quantity = item.get("quantity")
            products.append({"product_code": code, "product_name": item.get("productName"),
                             "quantity": quantity if isinstance(quantity, int) and quantity > 0 else 1})
        parsed.append({"order_id": order.get("orderId"), "created_at": order.get("createTime") or "",
                       "store_code": order.get("storeCode"), "store_name": order.get("storeName"),
                       "order_status": order.get("orderStatus"), "products": products,
                       "total_amount": order.get("realTotalAmount")})
    usable = [o for o in parsed
              if o["products"] and isinstance(o["store_code"], str) and o["store_code"].strip()]
    usable.sort(key=lambda o: o["created_at"], reverse=True)
    return usable


def last_order_spec(result, base):
    """把最近一次订单变成「跟上次一样」的候选规格；没有可用历史就返回 None。

    历史价格一律不复用：只复用门店与商品编码，必须重新核价。
    """
    history = order_history(result)
    if not history:
        return None
    last = history[0]
    spec = dict(base)
    spec["store"] = {"code": last["store_code"], "name": last["store_name"]}
    spec["candidates"] = [{"id": "last-order", "product_code": product["product_code"],
                           "label": product.get("product_name") or "上次点的商品", "spicy": None}
                          for product in last["products"]]
    spec["source_order"] = {"order_id": last["order_id"], "created_at": last["created_at"],
                            "store_name": last["store_name"], "order_status": last["order_status"],
                            "note": "按同一家店重新核价，不复用历史价格。"}
    return spec


def available_basket(client, plan, items):
    """逐件试核价，剔除当前不可售的商品。返回 (可用件, 被剔除件+原因)。

    不替换、不静默：剔除项必须由调用方明确告知用户。
    单点核价 <= 0 的也剔除——那说明它是套餐内部构成项，不是可单点商品。
    """
    base = order_context(plan)
    kept, dropped = [], []
    for item in items:
        try:
            quote = client.call("calculate-price", dict(base, items=[{"productCode": item["product_code"],
                                                                      "quantity": item.get("quantity", 1)}]))
        except MCPError as exc:
            dropped.append({"item": item, "reason": str(exc)})
            continue
        payload = tool_payload(quote) or (quote if isinstance(quote, dict) else {})
        price = payload.get("price")
        if not isinstance(price, int) or price <= 0:
            dropped.append({"item": item, "reason": "单点核价为 0 或缺失，属套餐内部构成项，不能单独点"})
            continue
        kept.append(item)
    return kept, dropped


def fetch_basket_snapshot(client, plan, items, label=None):
    """对任意商品篮子做当次核价（用于「跟上次一样」复购，以及单品直选基线）。

    只复用商品编码与门店，**不复用历史价格**；篮子不做"完整一餐"结构判断。
    """
    if not items:
        raise ValueError("篮子为空，不能核价。")
    for item in items:
        if not isinstance(item.get("product_code"), str) or not item["product_code"]:
            raise ValueError("篮子商品缺少编码，停止核价。")
    base = order_context(plan)
    request = [{"productCode": i["product_code"], "quantity": i.get("quantity", 1)} for i in items]
    quote = client.call("calculate-price", dict(base, items=request))
    price = quoted_cents(quote)
    nutrition = nutrition_rows(client.call("list-nutrition-foods", {}))
    missing = [i.get("product_name") or i["product_code"] for i in items
               if i.get("product_name") not in nutrition]
    totals = {}
    for key in ("energy_kcal", "sodium_mg", "protein_g"):
        values = [nutrition.get(i.get("product_name"), {}).get(key) for i in items]
        totals[key] = None if any(v is None for v in values) else sum(values)
    return {"mode": "live", "store": plan.get("store", {}), "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "麦当劳官方 MCP：calculate-price + list-nutrition-foods",
            "price_policy": "所有金额以 calculate-price 返回的整数分为准；不复用历史订单金额。",
            "label": label or "本篮子", "items": items, "nutrition_missing": missing,
            "quote": {"price_cents": price,
                      "take_way_options": [{k: v.get(k) for k in ("code", "title", "subtitle")}
                                           for v in quote.get("takeWayList", [])],
                      "fees_cents": {k: quote.get(k) for k in ("deliveryPrice", "packingPrice", "tablewarePrice")}},
            **totals}


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
        display = display_price_report(menu.get("meals", {}).get(code), price)
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
                  "coupon_applied": None if coupon else False, "quote_tool": "calculate-price", **totals,
                  "display_price_cents": display["display_price_cents"],
                  "display_price_condition": display["display_price_condition"],
                  "display_price_note": display["display_price_note"]}
        results.append(result)
        if on_progress:
            on_progress(result)
    snapshot = {"mode": "live", "fulfillment": {"channel": plan.get("fulfillment", {}).get("channel", "pickup")}, "store": store, "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "麦当劳官方 MCP：calculate-price + list-nutrition-foods",
            "price_policy": "所有金额以 calculate-price 返回的整数分为准；菜单展示价仅作参考，附带条件（如随单购卡）必须与核价并列展示。",
            "scope": "仅比较本轮候选；不保证全菜单最低价；营养为标准份量的单品加总。", "plans": results}
    if plan.get("source_order"):
        snapshot["source_order"] = plan["source_order"]
    return snapshot
