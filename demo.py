#!/usr/bin/env python3
"""Offline snapshot by default; --live requests official MCP pricing explicitly."""
import argparse
import json
import sys
from pathlib import Path
from gourmet.core import default_pick, money_to_cents, order_card, pick_reason, review, select_plan
from gourmet.live import available_basket, fetch_basket_snapshot, fetch_snapshot, last_order_spec, store_coupons, coupon_choices
from gourmet.mcp import Client, MCPError
from gourmet.member import member_overview, points_products, points_detail, my_coupons
from gourmet.coupons import coupon_report, render_coupon_report
from gourmet.stores import search_stores, address_choices, delivery_stores
from gourmet.channels import order_context
ROOT = Path(__file__).resolve().parent

def main(argv=None):
    parser = argparse.ArgumentParser(description='麦门点餐议事会：完整餐单，透明取舍。')
    parser.add_argument('--budget', default='35', help='预算（元），默认 35')
    parser.add_argument('--taste', choices=['any', 'spicy', 'no-spicy'], default='any')
    parser.add_argument('--side', choices=['any', 'fries'], default='any')
    parser.add_argument('--sodium-limit', type=int, help='自定义钠上限 mg；不是医学建议')
    parser.add_argument('--live', action='store_true', help='使用本机 MCD_MCP_TOKEN 实时核价')
    parser.add_argument('--plan', type=Path, default=None)
    parser.add_argument('--input', type=Path, help='读取标准化报价 JSON')
    parser.add_argument('--json', action='store_true', help='输出结构化审阅结果')
    parser.add_argument('--compare', action='store_true', help='展开全部候选与「为什么不是它」；默认只给一个答案 + 点单卡')
    parser.add_argument('--any', action='store_true', help='不设预算：只按其他硬性条件给候选，并明确标注"未设预算"')
    parser.add_argument('--last', action='store_true', help='跟上次一样：读取最近一次订单的商品，按当次价重新核价（需 --live；找不到历史则退回默认）')
    parser.add_argument('--save-snapshot', type=Path, help='保存脱敏报价，不存 Token 或券 ID')
    parser.add_argument('--select', help='明确选择候选 ID，只记录选择，不下单')
    parser.add_argument('--list-tools', action='store_true', help='读取允许的 MCP 工具参数')
    parser.add_argument('--list-coupons', action='store_true', help='联网查询计划门店可用券，只显示名称与匹配候选，不输出券 ID')
    parser.add_argument('--coupon-title', help='使用查询返回的完整券名称；须与 --live、--coupon-candidate 配合')
    parser.add_argument('--coupon-candidate', help='只对这个候选 ID 提交用券核价，不改变其他候选')
    parser.add_argument('--member', action='store_true', help='显式查询自己的积分、券包和待领取券；不保存个人结果')
    parser.add_argument('--my-coupons', action='store_true', help='只读我的券：日期、时段、官方状态；可选门店与渠道核验')
    parser.add_argument('--coupon-demo', action='store_true', help='不联网，体验明确标记的构造券包样例')
    parser.add_argument('--points-products', action='store_true', help='查询积分餐品券目录，不兑换')
    parser.add_argument('--points-detail', type=int, metavar='SPU_ID', help='查询所选积分商品的 SKU 和两阶段费用，不兑换')
    parser.add_argument('--sugar', choices=['any','zero','regular'], default='any', help='饮料：不限 / 无糖 / 含糖；未知不满足指定条件')
    parser.add_argument('--energy-limit', type=int, help='个人能量上限 kcal，不是健康评分')
    parser.add_argument('--protein-min', type=int, help='个人蛋白质下限 g')
    parser.add_argument('--freshness-minutes', type=int, default=15, help='本工具实时核价复核窗口 1～60 分钟')
    parser.add_argument('--max-response-mb', type=int, default=8, choices=range(1,65), metavar='1..64', help='MCP 响应大小上限 MB，超限停止而非截断使用')
    parser.add_argument('--search-stores', action='store_true', help='按城市和地点关键词查门店')
    parser.add_argument('--city', help='门店搜索城市')
    parser.add_argument('--keyword', help='地点关键词，例如地铁站或商场')
    parser.add_argument('--store-code', help='从搜索结果中选定的门店编码；不自动定位')
    parser.add_argument('--expand', action='store_true', help='实时枚举选定套餐的已识别小食×饮料组合，逐份核价，最多12份')
    parser.add_argument('--ice', choices=['any','standard','less','none','extra'], default='any', help='饮料冰量：不限/标准/少冰/去冰/多冰；实时按官方特调核价')
    parser.add_argument('--people', type=int, default=1, help='就餐人数 1～8：主食与饮料各 ≥ 人数、小食 ≥ 1')
    parser.add_argument('--budget-scope', choices=['total','per_person'], default='total', help='预算口径：整单（默认）或人均')
    parser.add_argument('--baseline-plan', help='把本店某份候选当作"你本来会点的"，用于计算省了多少钱')
    parser.add_argument('--baseline-cents', type=int, metavar='分', help='外部真实核价基线（整数分），必须与 --baseline-store 同店')
    parser.add_argument('--baseline-store', help='基线报价所属门店编码，必须与本轮门店一致')
    parser.add_argument('--baseline-label', help='基线的可读说明，例如「单品直选：巨无霸+薯条+可乐」')
    parser.add_argument('--omit', action='append', default=[], metavar='配料原名', help='去除主食配料，可重复；必须匹配官方特调名称，营养数据改为未知')
    parser.add_argument('--channel', choices=['pickup','drive','delivery'], default='pickup', help='到店 / 得来速 / 麦乐送；菜单、券和核价使用同一场景')
    parser.add_argument('--business-code', help='得来速或配送门店返回的 beCode，必须与 storeCode 配对')
    parser.add_argument('--addresses', action='store_true', help='显式查询脱敏地址引用，不输出姓名电话门牌')
    parser.add_argument('--delivery-stores', action='store_true', help='查询所选地址可配送的门店')
    parser.add_argument('--address-ref', help='从 --addresses 选择的稳定地址引用')
    parser.add_argument('--list-meals', action='store_true', help='查看所选门店当次菜单名称与编码')
    parser.add_argument('--meal-code', action='append', default=[], help='从当次菜单选择的套餐编码，可重复；替代样例套餐，不沿用原模板属性')
    args = parser.parse_args(argv)
    try:
        def client():
            return Client(max_response_bytes=args.max_response_mb * 1_000_000)
        if (args.city or args.keyword) and not args.search_stores:
            raise ValueError('--city 和 --keyword 仅用于 --search-stores。')
        if args.store_code and not (args.live or args.list_coupons or args.list_meals or args.my_coupons):
            raise ValueError('切换门店必须实时核价或查询门店券；历史快照不能改门店。')
        if args.expand and not args.live:
            raise ValueError('--expand 必须与 --live 一起使用，每份组合重新官方核价。')
        if args.omit and not args.live:
            raise ValueError('去配料必须实时读取特调并核价，不修改历史营养值。')
        actions = [args.addresses, args.delivery_stores, args.search_stores, args.member, args.my_coupons, args.coupon_demo, args.points_products, args.points_detail is not None, args.list_coupons, args.list_tools, args.list_meals]
        if sum(actions) > 1 or (any(actions) and (args.live or args.input or args.select or args.save_snapshot or args.coupon_title or args.coupon_candidate)):
            raise ValueError('独立查询入口不能相互混用，也不能与核价、快照保存或选择混用。')
        if args.address_ref is not None and not args.delivery_stores:
            raise ValueError('--address-ref 仅与 --delivery-stores 配合。')
        if args.business_code and not (args.live or args.list_coupons or args.list_meals or args.my_coupons):
            raise ValueError('--business-code 仅用于所选场景的实时核价或券查询。')
        if args.channel != 'pickup' and not (args.live or args.list_coupons or args.list_meals or args.my_coupons or args.search_stores or args.points_detail or args.addresses or args.delivery_stores):
            raise ValueError('不能把历史到店快照改成其他渠道；请使用相应实时查询入口。')
        if args.my_coupons or args.coupon_demo:
            if args.plan or args.meal_code or args.ice != 'any':
                raise ValueError('券包清点不修改餐单；门店核验请传 --store-code 和对应渠道，核价另行执行。')
            if args.coupon_demo:
                example = json.loads((ROOT / 'fixtures/coupon-demo.json').read_text(encoding='utf-8'))
                value = coupon_report(example['coupons'], len(example['coupons']), True,
                                      now=example['reference_time'], mode='synthetic')
            else:
                if not args.store_code and (args.business_code or args.channel != 'pickup'):
                    raise ValueError('按渠道核验券须提供所选门店；得来速/配送还须提供同次查询的业务编码。')
                context = {'store':{'code':args.store_code}, 'fulfillment':{'channel':args.channel, 'be_code':args.business_code}} if args.store_code else None
                value = my_coupons(client(), context)
            print(json.dumps(value, ensure_ascii=False, indent=2) if args.json else render_coupon_report(value))
            return 0
        if args.addresses or args.delivery_stores:
            value = address_choices(client()) if args.addresses else delivery_stores(client(), args.address_ref)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.search_stores:
            value = search_stores(client(), args.city, args.keyword, args.channel)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.member or args.points_products or args.points_detail is not None:
            connection = client()
            value = member_overview(connection) if args.member else points_products(connection) if args.points_products else points_detail(connection, args.points_detail)
            if args.points_detail is not None:
                value['requested_channel'] = args.channel
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if not 1 <= args.freshness_minutes <= 60 or any(v is not None and v <= 0 for v in (args.sodium_limit,args.energy_limit,args.protein_min)):
            raise ValueError('营养条件须为正整数，复核窗口须为 1～60 分钟。')
        budget = None if args.any else money_to_cents(args.budget)
        plan = None
        if args.live or args.list_coupons or args.list_meals:
            if not args.store_code and args.plan is None:
                raise ValueError('请先选门店：--search-stores --city 城市 --keyword 地点，然后用 --store-code 编码；或显式指定已确认的 --plan 文件。')
            plan = json.loads(args.plan.read_text(encoding='utf-8')) if args.plan else {'candidates': []}
            if args.store_code:
                if not args.store_code.isdigit():
                    raise ValueError('门店编码必须是数字字符串。')
                if args.plan and plan.get('store', {}).get('code') != args.store_code and plan.get('candidates') and not args.meal_code:
                    raise ValueError('切换计划门店时请重新用 --meal-code 选择当前菜单餐品；不继承旧门店的餐品或优惠券。')
                if args.plan and plan.get('store', {}).get('code') != args.store_code and plan.get('fulfillment', {}).get('channel', 'pickup') != 'pickup' and (args.channel == 'pickup' or not args.business_code):
                    raise ValueError('切换配送或得来速门店时必须重新明确 --channel 和成对 --business-code，不沿用旧业务编码。')
                plan['store'] = {'code':args.store_code, 'name':'所选门店 '+args.store_code}
            if args.channel != 'pickup' or args.business_code:
                plan['fulfillment'] = {'channel':args.channel, 'be_code':args.business_code}
            if args.last:
                connection = client()
                spec = last_order_spec(connection.call('order-list', {}), plan)
                if spec is None:
                    print('没有可复用的历史订单，按默认来。', file=sys.stderr)
                else:
                    # 先确认"上次那家店"现在可用（菜单拉得到=在营业）；不可用就明说并退回默认。
                    try:
                        connection.call('query-meals', dict(order_context(spec)))
                    except MCPError as exc:
                        print('上次那家店（%s）现在不可用：%s' % (spec['store'].get('name', ''), exc), file=sys.stderr)
                        print('已退回按当前条件给默认方案。', file=sys.stderr)
                        spec = None
                if spec is not None:
                    kept, dropped = available_basket(connection, spec, spec['candidates'])
                    for entry in dropped:
                        print('上次的「%s」现在不可用：%s（已去掉，不替换）'
                              % (entry['item'].get('product_name') or entry['item']['product_code'], entry['reason']), file=sys.stderr)
                    if not kept:
                        print('上次的商品现在都不可用，已退回按当前条件给默认方案。', file=sys.stderr)
                        spec = None
                    else:
                        spec['candidates'] = kept
                if spec is not None:
                    basket = fetch_basket_snapshot(connection, spec, spec['candidates'], label='跟上次一样')
                    print('跟上次一样（%s 于 %s）' % (spec['source_order']['created_at'], spec['source_order']['store_name']))
                    for index, item in enumerate(basket['items'], 1):
                        print('  %d. %s ×%d' % (index, item.get('product_name') or item['product_code'], item.get('quantity', 1)))
                    ways = basket['quote']['take_way_options'] or []
                    way = ways[0]['title'] if ways and isinstance(ways[0], dict) else '到店自取'
                    print('  当次核价：¥%.2f（%s · %s）' % (basket['quote']['price_cents'] / 100, basket['store'].get('name', ''), way))
                    if basket['nutrition_missing']:
                        print('  营养数据缺失：%s（按未知处理，不当作 0）' % '、'.join(basket['nutrition_missing']))
                    print('  %s' % spec['source_order']['note'])
                    print('  这是记录，不是下单；没有支付。')
                    return 0
            if args.meal_code:
                if len(set(args.meal_code)) != len(args.meal_code) or len(args.meal_code) > 3 or not all(c.isdigit() for c in args.meal_code):
                    raise ValueError('请选择最多 3 个不同的有效套餐编码。')
                plan['candidates'] = [{'id':code,'product_code':code,'label':'当次默认搭配'} for code in args.meal_code]
            if args.live and not plan.get('candidates'):
                raise ValueError('请先用 --list-meals --store-code 编码 查看当次菜单，再用 --meal-code 选择套餐；不自动套用演示餐品。')
            print('本轮所选门店：%s（%s）' % (plan['store']['name'], plan['store']['code']), file=sys.stderr)
        if args.meal_code and not (args.live or args.list_coupons):
            raise ValueError('--meal-code 只用于实时核价或匹配门店券。')
        if args.list_meals:
            menu = client().call('query-meals', order_context(plan))
            if not isinstance(menu, dict) or not isinstance(menu.get('meals'), dict):
                raise MCPError('无法识别菜单。')
            print(json.dumps({'meals':[{'code':code,'name':item.get('name')} for code,item in menu['meals'].items()],
                              'notice':'从当次菜单选择套餐编码 --meal-code；目前程序只构造三轮完整套餐。单品和其他结构不会当作完整餐单。'}, ensure_ascii=False, indent=2))
            return 0
        if args.live and args.input:
            raise ValueError('--live 与 --input 不能同时使用。')
        if (args.coupon_title or args.coupon_candidate) and not args.live:
            raise ValueError('用券仅支持显式 --live，不修改历史快照。')
        if args.list_coupons and (args.live or args.input or args.select or args.save_snapshot or args.list_tools):
            raise ValueError('--list-coupons 是独立查询，请不要与核价、选择或保存操作混用。')
        if args.list_coupons:
            choices = coupon_choices(store_coupons(client(), plan), plan)
            print(json.dumps({'store': plan['store'], 'coupons': choices,
                              'notice': '仅查询，不领券。candidate_ids 为空表示当前候选不支持该券；不会自动用券。'},
                             ensure_ascii=False, indent=2))
            return 0
        if args.list_tools:
            print(json.dumps(client().tools(), ensure_ascii=False, indent=2))
            return 0
        if args.live:
            print('模式：本轮官方实时核价。', file=sys.stderr)
            data = fetch_snapshot(client(), plan, coupon_title=args.coupon_title,
                                  coupon_candidate=args.coupon_candidate, expand=args.expand, ice=args.ice, omit=args.omit)
        else:
            data = json.loads((args.input or ROOT / 'fixtures/snapshot.json').read_text(encoding='utf-8'))
        result = review(data, budget, args.taste, args.sodium_limit, args.side, sugar=args.sugar,
                        energy_limit=args.energy_limit, protein_min=args.protein_min, freshness_minutes=args.freshness_minutes, ice=args.ice,
                        people=args.people, budget_scope=args.budget_scope,
                        baseline_plan_id=args.baseline_plan, baseline_cents=args.baseline_cents,
                        baseline_label=args.baseline_label, baseline_store_code=args.baseline_store)
        print(result['data_notice'], file=sys.stderr)
        print('门店：%s；数据时间：%s' % (data['store']['name'], data['captured_at']), file=sys.stderr)
        if args.save_snapshot:
            args.save_snapshot.write_text(json.dumps(dict(data, mode='synthetic' if data['mode'] == 'synthetic' else 'snapshot'), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if args.select:
            result['selected'] = select_plan(result, args.select, result['review_id'])
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            label = result['data_notice']
            print('麦门点餐议事会 | ' + label)
            print(data['store']['name'], '|', data['captured_at'])
            req = result['requirements']
            if req['budget_unspecified']:
                scope = ('%d 人，主食与饮料各 ≥ %d 份、小食 ≥ 1 份' % (req['people'], req['people'])) if req['people'] > 1 else '主食＋小食＋饮料各至少一份'
                print('需求：%s；未设预算（只按其他硬性条件筛）' % scope)
            elif req['people'] > 1:
                if req['budget_scope'] == 'per_person':
                    print('需求：%d 人；主食与饮料各 ≥ %d 份、小食 ≥ 1 份；人均预算 ¥%.2f（整单上限 ¥%.2f）'
                          % (req['people'], req['people'], budget / 100, req['effective_budget_cents'] / 100))
                else:
                    print('需求：%d 人；主食与饮料各 ≥ %d 份、小食 ≥ 1 份；整单预算 ¥%.2f'
                          % (req['people'], req['people'], budget / 100))
            else:
                print('需求：主食＋小食＋饮料各至少一份；预算 ¥%.2f' % (budget / 100))
            pick = default_pick(result)
            if pick:
                ways = pick.get('take_way_options') or []
                way = ways[0].get('title') if ways and isinstance(ways[0], dict) else '到店自取'
                print('\n这顿就它了 👇\n')
                print('  %s · %s' % (pick['name'], pick['variant']))
                print('  ¥%.2f   %s · %s' % (pick['price_cents'] / 100, result['store']['name'], way))
                print('  %s' % pick_reason(result, pick['id']))
                if pick.get('display_price_note'):
                    print('  ⚠️ %s' % pick['display_price_note'])
                print('\n点单卡（可复制）')
                for line in order_card(result, pick['id'])['lines']:
                    print('  ' + line)
                print('\n想看别的：加 --compare 展开全部候选与「为什么不是它」。')
            if args.compare:
                for p in result['plans']:
                    print('\n[%s] %s · %s：¥%.2f' % (p['id'], p['name'], p['variant'], p['price_cents'] / 100))
                    print('  ' + ' + '.join(i['name'] + ('（'+ '、'.join(i['customizations'])+'）' if i.get('customizations') else '') for i in p['items']))
                    print('  钠：%s；能量：%s' % (str(p['sodium_mg']) + ' mg' if p['sodium_mg'] is not None else '未知', str(p['energy_kcal']) + ' kcal' if p['energy_kcal'] is not None else '未知'))
                    if result['requirements']['people'] > 1:
                        print('  人均 ¥%.2f（%d 人）｜结构：%s' % (p['per_person_cents'] / 100, result['requirements']['people'], p['structure']))
                    if result.get('baseline') and 'saving_cents' in p:
                        if p['saving_cents'] > 0:
                            print('  比「%s」省 ¥%.2f（%.1f%%）' % (result['baseline']['label'], p['saving_cents'] / 100, p['saving_percent']))
                        elif p['saving_cents'] < 0:
                            print('  比「%s」贵 ¥%.2f' % (result['baseline']['label'], -p['saving_cents'] / 100))
                        else:
                            print('  就是基线本身')
                    print('  ' + ('符合当前硬性条件' if p['eligible'] else '；'.join(p['reasons'])))
                print('\n三个规则审阅器：', result['reviewers'])
                print('价格与钠的取舍候选：', ', '.join(result['tradeoffs']['price_sodium']) or '无')
                print('口味与钠的取舍候选：', ', '.join(result['tradeoffs']['taste_sodium']) or '无')
                print('多维营养取舍候选：', ', '.join(result['tradeoffs']['nutrition_multi']) or '无')
                reasons = result.get('tradeoff_reasons', {})
                axis_titles = {'price_sodium': '价格与钠', 'taste_sodium': '口味与钠', 'nutrition_multi': '多维营养'}
                shown = 0
                for name in ('price_sodium', 'taste_sodium', 'nutrition_multi'):
                    for plan_id, info in (reasons.get(name, {}).get('dominated') or {}).items():
                        if shown >= 4:
                            break
                        print('  从「%s」角度看，为什么没有 %s：被 %s 比下去——%s'
                              % (axis_titles[name], plan_id, info['by'], '；'.join(info['why'])))
                        shown += 1
                if result.get('best_saving'):
                    print('最省的是 %s：比「%s」省 ¥%.2f（%.1f%%）'
                          % (result['best_saving']['plan_id'], result['baseline']['label'],
                             result['best_saving']['saving_cents'] / 100, result['best_saving']['saving_percent']))
            if not pick:
                ladder = result.get('budget_ladder') or {}
                if ladder.get('steps'):
                    print('\n预算阶梯（只调整预算，不放宽口味、小食、饮料或营养条件）：')
                    for step in ladder['steps']:
                        print('  预算 ¥%.2f → 可选 %d 份（比现在多 ¥%.2f）'
                              % (step['budget_cents'] / 100, step['candidates'], step['increase_cents'] / 100))
                print(result['next_step'])
            elif args.compare:
                print(result['next_step'])
            if not pick or args.compare:
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
