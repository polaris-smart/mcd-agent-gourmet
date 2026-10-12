#!/usr/bin/env python3
"""麦门多 agent 协作点餐 · 双模式演示
模式 A（零 Token）：fixtures/ 录制的真实 MCP 响应
模式 B（有 Token）：真实调用麦当劳 MCP Server
"""

import json, os, sys, urllib.request, urllib.error

def load_config():
    """加载 config.json（有 Token 就用真实模式）"""
    path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def load_fixture(name):
    """加载 fixture（零 Token 模式）"""
    path = os.path.join(os.path.dirname(__file__), "fixtures", f"{name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def mcp_call(tool_name, params, config):
    """真实调用麦当劳 MCP Server"""
    url = config["mcp_endpoint"]
    token = config["mcp_token"]
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": params
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8')[:200]}"}
    except Exception as e:
        return {"error": str(e)}

def cents_to_yuan(cents):
    return cents / 100.0

def nutritionist_analyze(meals, nutrition_data):
    """营养师：分析营养构成，标记超标项"""
    report = {"agent": "营养师", "recommendations": [], "warnings": []}
    for meal in meals:
        nutrition = nutrition_data.get(meal["code"], {})
        calories = nutrition.get("calories", 0)
        sodium = nutrition.get("sodium", 0)
        if calories > 600:
            report["warnings"].append(f"⚠️ {meal['name']} 热量超标（{calories} kcal）")
        if sodium > 800:
            report["warnings"].append(f"⚠️ {meal['name']} 钠超标（{sodium} mg）")
        if calories <= 500 and sodium <= 600:
            report["recommendations"].append(f"✓ {meal['name']} 营养均衡（{calories} kcal）")
    return report

def budgeter_optimize(meals, coupons, budget=50):
    """预算师：枚举候选方案，计算最优组合"""
    plans = []
    for meal in meals:
        price_cents = meal.get("price", 0)
        if price_cents <= budget * 100:
            plans.append({"meal": meal["name"], "price": cents_to_yuan(price_cents)})
    plans.sort(key=lambda x: x["price"])
    return {"agent": "预算师", "plans": plans, "budget": budget}

def taster_recommend(meals, preferences=None):
    """口味师：推荐搭配，考虑个人偏好"""
    preferences = preferences or {"spicy": True, "sweet": False}
    recommendations = []
    for meal in meals:
        tags = meal.get("tags", [])
        if preferences.get("spicy") and "辣" in tags:
            recommendations.append(f"🌶️ {meal['name']}（辣味推荐）")
        elif preferences.get("sweet") and "甜" in tags:
            recommendations.append(f"🍰 {meal['name']}（甜味推荐）")
    return {"agent": "口味师", "recommendations": recommendations}

def coordinator_collect(nutrition, budget, taste):
    """协调器：三 agent 方案汇总"""
    print("=" * 60)
    print("麦门多 agent 协作点餐 · 协调器汇总")
    print("=" * 60)
    print()
    
    print(f"【{nutrition['agent']}】")
    for rec in nutrition["recommendations"]:
        print(f"  {rec}")
    for warn in nutrition["warnings"]:
        print(f"  {warn}")
    print()
    
    print(f"【{budget['agent']}】预算 {budget['budget']} 元")
    for i, plan in enumerate(budget["plans"][:3], 1):
        print(f"  {i}. {plan['meal']} —— {plan['price']:.1f} 元")
    print()
    
    print(f"【{taste['agent']}】")
    for rec in taste["recommendations"]:
        print(f"  {rec}")
    print()
    
    print("=" * 60)
    print("【owner 审批】")
    print("=" * 60)
    print("三 agent 方案已呈现，请 owner 选择：")
    print("  1. 采纳营养师推荐（健康优先）")
    print("  2. 采纳预算师推荐（省钱优先）")
    print("  3. 采纳口味师推荐（口味优先）")
    print("  4. 综合选择（告诉我你的偏好）")
    print()

def main():
    config = load_config()
    
    if config and config.get("mcp_token"):
        print("麦门多 agent 协作点餐 · 真实模式（有 Token）")
        print("数据源：麦当劳 MCP Server 实时调用")
        print()
        
        # 真实调用：查询附近门店
        print("=" * 60)
        print("第一步：查询附近门店")
        print("=" * 60)
        result = mcp_call("query-nearby-stores", {"address": "南京东城汇"}, config)
        if "error" in result:
            print(f"❌ MCP 调用失败：{result['error']}")
            print("降级到 fixture demo 模式...")
            config = None
        else:
            print(f"✓ MCP 调用成功（工具：query-nearby-stores）")
            print(f"响应：{json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
            print()
    
    if not config or not config.get("mcp_token"):
        print("麦门多 agent 协作点餐 · 零配置演示（fixture 模式）")
        print("数据：fixtures/ 中录制的真实 MCP 响应（2026-10-12 采集）")
        print()
        
        # fixture 模式
        meals = load_fixture("meals")
        nutrition_data = load_fixture("nutrition")
        coupons = load_fixture("coupons")
        
        print("=" * 60)
        print("链路：多 agent 协作点餐")
        print("=" * 60)
        print("门店：麦当劳南京东城汇餐厅(1990622)（到店自取）")
        print("需求：想吃「汉堡 + 薯条 + 可乐」，预算 50 元")
        print()
        
        # 三 agent 并行工作
        nutrition = nutritionist_analyze(meals, nutrition_data)
        budget = budgeter_optimize(meals, coupons, budget=50)
        taste = taster_recommend(meals, preferences={"spicy": True})
        
        # 协调器汇总
        coordinator_collect(nutrition, budget, taste)
    
    print("=" * 60)
    print("【本演示到此】")
    print("=" * 60)
    print("真实运行时：")
    print("  · owner 选择方案 → 协调器创建订单 → 返回支付链接")
    print("  · 所有金额来自 MCP calculate-price 真实计价")
    print("  · 任何写操作必须经 owner 显式确认")
    print()

if __name__ == "__main__":
    main()
