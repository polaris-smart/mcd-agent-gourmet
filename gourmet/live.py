"""A bounded set of complete meals, verified against live menu/detail/price."""

import csv
import re
from datetime import datetime, timezone
from .mcp import MCPError


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


def assemble(detail, replacements):
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
        rounds.append({"round": str(group["id"]), "comboItemList": [{"code": choice["code"], "quantity": 1}]})
        items.append({"code": choice["code"], "name": choice["name"], "quantity": 1,
                      "kind": kind, "is_fries": kind == "side" and "薯条" in choice["name"]})
    return {"productCode": detail["code"], "quantity": 1, "roundList": rounds}, items


def quoted_cents(value):
    price = value.get("price") if isinstance(value, dict) else None
    if type(price) is not int or price < 0:
        raise MCPError("官方核价缺少整数分 price 字段；不使用菜单展示价替代。")
    return price


def fetch_snapshot(client, plan, on_progress=None):
    store, specs = plan["store"], plan["candidates"]
    if not 1 <= len(specs) <= 12:
        raise ValueError("一次最多核价 12 份餐单。")
    if not isinstance(store.get("code"), str) or not store["code"].isdigit():
        raise ValueError("门店编码必须是数字字符串。")
    base = {"storeCode": store["code"], "beType": 1, "orderType": 1}
    menu = client.call("query-meals", base)
    nutrition = nutrition_rows(client.call("list-nutrition-foods", {}))
    client.call("query-store-coupons", base)  # Never store or publish account-specific coupons.
    details, results = {}, []
    for spec in specs:
        code = spec["product_code"]
        if code not in menu.get("meals", {}):
            raise MCPError("当前门店没有候选套餐；请重新选餐，不沿用旧数据。")
        if code not in details:
            details[code] = client.call("query-meal-detail", dict(base, code=code))
        request_item, items = assemble(details[code], spec.get("replacements", {}))
        coupon = spec.get("coupon")
        if coupon is not None:
            if not isinstance(coupon, dict) or set(coupon) != {"couponId", "couponCode"} or not all(isinstance(v, str) and v for v in coupon.values()):
                raise ValueError("优惠券必须同时提供有效 couponId 与 couponCode。")
            request_item.update(coupon)
        quote = client.call("calculate-price", dict(base, items=[request_item]))
        price = quoted_cents(quote)
        totals = {}
        missing = [i["name"] for i in items if i["name"] not in nutrition]
        for key in ("energy_kcal", "sodium_mg", "protein_g"):
            values = [nutrition.get(i["name"], {}).get(key) for i in items]
            totals[key] = None if any(v is None for v in values) else sum(values)
        result = {"id": spec["id"], "name": details[code]["name"], "variant": spec["label"],
                  "store_code": store["code"], "items": items, "price_cents": price,
                  "spicy": spec.get("spicy"), "nutrition_missing": missing,
                  "coupon_applied": coupon is not None, "quote_tool": "calculate-price", **totals}
        results.append(result)
        if on_progress:
            on_progress(result)
    return {"mode": "live", "store": store, "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "麦当劳官方 MCP：calculate-price + list-nutrition-foods",
            "scope": "仅比较本轮候选；不保证全菜单最低价；营养为标准份量的单品加总。", "plans": results}
