#!/usr/bin/env python3
"""Offline snapshot by default; --live requests official MCP pricing explicitly."""
import argparse
import json
import sys
from pathlib import Path
from gourmet.core import money_to_cents, review, select_plan
from gourmet.live import fetch_snapshot
from gourmet.mcp import Client, MCPError
ROOT = Path(__file__).resolve().parent

def main(argv=None):
    parser = argparse.ArgumentParser(description='麦门点餐议事会：完整餐单，透明取舍。')
    parser.add_argument('--budget', default='35', help='预算（元），默认 35')
    parser.add_argument('--taste', choices=['any', 'spicy', 'no-spicy'], default='spicy')
    parser.add_argument('--side', choices=['any', 'fries'], default='any')
    parser.add_argument('--sodium-limit', type=int, help='自定义钠上限 mg；不是医学建议')
    parser.add_argument('--live', action='store_true', help='使用本机 MCD_MCP_TOKEN 实时核价')
    parser.add_argument('--plan', type=Path, default=ROOT / 'fixtures/plan.json')
    parser.add_argument('--input', type=Path, help='读取标准化报价 JSON')
    parser.add_argument('--json', action='store_true', help='输出结构化审阅结果')
    parser.add_argument('--save-snapshot', type=Path, help='保存脱敏报价，不存 Token 或券 ID')
    parser.add_argument('--select', help='明确选择候选 ID，只记录选择，不下单')
    parser.add_argument('--list-tools', action='store_true', help='读取允许的 MCP 工具参数')
    args = parser.parse_args(argv)
    try:
        budget = money_to_cents(args.budget)
        if args.live and args.input:
            raise ValueError('--live 与 --input 不能同时使用。')
        if args.list_tools:
            print(json.dumps(Client().tools(), ensure_ascii=False, indent=2))
            return 0
        if args.live:
            data = fetch_snapshot(Client(), json.loads(args.plan.read_text(encoding='utf-8')))
        else:
            data = json.loads((args.input or ROOT / 'fixtures/snapshot.json').read_text(encoding='utf-8'))
        result = review(data, budget, args.taste, args.sodium_limit, args.side)
        if args.save_snapshot:
            args.save_snapshot.write_text(json.dumps(dict(data, mode='snapshot'), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if args.select:
            result['selected'] = select_plan(result, args.select, result['review_id'])
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            label = '本轮实时核价' if data['mode'] == 'live' else '历史快照演示 · 当前购买须重新核价'
            print('麦门点餐议事会 | ' + label)
            print(data['store']['name'], '|', data['captured_at'])
            print('需求：主食＋小食＋饮料各至少一份；预算 ¥%.2f' % (budget / 100))
            for p in result['plans']:
                print('\n[%s] %s · %s：¥%.2f' % (p['id'], p['name'], p['variant'], p['price_cents'] / 100))
                print('  ' + ' + '.join(i['name'] for i in p['items']))
                print('  钠：%s；能量：%s' % (str(p['sodium_mg']) + ' mg' if p['sodium_mg'] is not None else '未知', str(p['energy_kcal']) + ' kcal' if p['energy_kcal'] is not None else '未知'))
                print('  ' + ('符合当前硬性条件' if p['eligible'] else '；'.join(p['reasons'])))
            print('\n三个规则审阅器：', result['reviewers'])
            print('观点存在差异，由你选择。' if result['disagreement'] else '当前条件下意见一致，或没有可选方案。')
            if result['selected']:
                print('已记录餐单选择；未创建订单，未支付。')
            print('仅比较上述候选，不保证全菜单最低价；不构成营养或医疗建议。')
        return 0
    except (MCPError, ValueError, KeyError, OSError) as exc:
        print('本轮停止：' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
