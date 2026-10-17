"""v1 · P1-2：零输入入口（不设预算 / 跟上次一样）。"""

import copy
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock

import demo

from gourmet.core import default_pick, review
from gourmet.live import (available_basket, fetch_basket_snapshot, last_order_spec,
                          order_history, tool_payload)
from gourmet.mcp import MCPError, READ_TOOLS

ROOT = Path(__file__).resolve().parents[1]


class NoBudget(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'fixtures/snapshot.json').read_text())

    def test_no_budget_drops_only_the_budget_constraint(self):
        result = review(self.data, budget_cents=None, taste='spicy')
        self.assertTrue(all(not any(r.startswith('超预算') for r in p['reasons']) for p in result['plans']))
        req = result['requirements']
        self.assertTrue(req['budget_unspecified'])
        self.assertIsNone(req['budget_cents'])
        self.assertIsNone(req['effective_budget_cents'])
        self.assertTrue(all(p['remaining_cents'] is None for p in result['plans']))
        self.assertEqual(result['budget_ladder'], {'needed_cents': None, 'steps': []})
        self.assertIn('未设预算', result['next_step'])
        self.assertEqual(result['feasible_count'], 6)

    def test_no_budget_still_enforces_hard_constraints(self):
        result = review(self.data, budget_cents=None, taste='no-spicy')
        self.assertTrue(all(not p['eligible'] for p in result['plans'] if p['spicy']))

    def test_per_person_scope_without_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            review(self.data, budget_cents=None, budget_scope='per_person')

    def test_invalid_budgets_still_rejected(self):
        for bad in (0, -1, '35', 35.0):
            with self.assertRaises(ValueError):
                review(self.data, budget_cents=bad)

    def test_default_pick_still_works_without_budget(self):
        result = review(self.data, budget_cents=None)
        pick = default_pick(result)
        self.assertEqual(pick['price_cents'], min(p['price_cents'] for p in result['plans'] if p['eligible']))


class OrderHistory(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / 'fixtures/order-history-sample.json').read_text())['payload']

    def test_parses_real_capture(self):
        history = order_history(self.payload)
        self.assertEqual(len(history), 1)
        last = history[0]
        self.assertEqual(last['store_code'], '已脱敏')
        self.assertEqual(last['created_at'], '2026-07-23 19:32:49')
        self.assertEqual([p['product_code'] for p in last['products']], ['9900008751', '1700'])
        self.assertTrue(all(p['quantity'] >= 1 for p in last['products']))

    def test_newest_order_first(self):
        payload = copy.deepcopy(self.payload)
        orders = payload['data']['list']
        older = copy.deepcopy(orders[0]); older['createTime'] = '2026-01-01 10:00:00'
        newer = copy.deepcopy(orders[0]); newer['createTime'] = '2026-10-01 10:00:00'
        payload['data']['list'] = [older, orders[0], newer]
        history = order_history(payload)
        self.assertEqual([o['created_at'] for o in history],
                         ['2026-10-01 10:00:00', '2026-07-23 19:32:49', '2026-01-01 10:00:00'])

    def test_malformed_payloads_are_empty_not_guessed(self):
        for bad in ({}, {'data': {}}, {'data': {'list': None}}, {'data': {'list': [None, 'x', 3]}}, None):
            self.assertEqual(order_history(bad), [])

    def test_orders_missing_store_or_products_are_dropped(self):
        payload = {'data': {'list': [
            {'orderId': 'a', 'storeCode': '', 'orderProductList': [{'productCode': '1'}]},
            {'orderId': 'b', 'storeCode': '1990000', 'orderProductList': []},
            {'orderId': 'c', 'storeCode': '1990000', 'orderProductList': [{'productCode': ''}, {'productCode': '77'}]},
        ]}}
        history = order_history(payload)
        self.assertEqual([o['order_id'] for o in history], ['c'])
        self.assertEqual([p['product_code'] for p in history[0]['products']], ['77'])

    def test_spec_reuses_store_and_codes_but_notes_repricing(self):
        spec = last_order_spec(self.payload, {'store': {'code': '1990001', 'name': '旧店'}, 'fulfillment': {'channel': 'pickup'}})
        self.assertEqual(spec['store']['code'], '已脱敏')
        self.assertEqual([c['product_code'] for c in spec['candidates']], ['9900008751', '1700'])
        self.assertIn('不复用历史价格', spec['source_order']['note'])

    def test_spec_is_none_without_usable_history(self):
        self.assertIsNone(last_order_spec({'data': {'list': []}}, {'store': {'code': '1'}}))


class Basket(unittest.TestCase):
    def setUp(self):
        self.plan = {'store': {'code': '1990000', 'name': '演示门店'}, 'fulfillment': {'channel': 'pickup'}}
        self.client = Mock()
        self.client.call.side_effect = lambda name, args=None: {
            'calculate-price': {'price': 2350, 'takeWayList': [{'code': 'take-in-store', 'title': '外带', 'subtitle': '店内自提'}]},
            'list-nutrition-foods': [{'productName': '可乐', 'energyKcal': '150', 'sodium': '20', 'protein': '0'}],
        }[name]

    def test_basket_quotes_afresh_and_sums_known_nutrition(self):
        basket = fetch_basket_snapshot(self.client, self.plan, [{'product_code': '9900008751', 'product_name': '可乐', 'quantity': 1}])
        self.assertEqual(basket['quote']['price_cents'], 2350)
        self.assertEqual(basket['sodium_mg'], 20.0)
        self.assertEqual(basket['energy_kcal'], 150.0)
        self.assertEqual(basket['nutrition_missing'], [])
        self.assertIn('不复用历史订单金额', basket['price_policy'])

    def test_unknown_item_makes_totals_unknown_not_zero(self):
        basket = fetch_basket_snapshot(self.client, self.plan, [
            {'product_code': '9900008751', 'product_name': '可乐', 'quantity': 1},
            {'product_code': '1700', 'product_name': '未知商品', 'quantity': 1},
        ])
        self.assertIsNone(basket['sodium_mg'])
        self.assertEqual(basket['nutrition_missing'], ['未知商品'])

    def test_empty_or_codeless_basket_is_rejected(self):
        with self.assertRaises(ValueError):
            fetch_basket_snapshot(self.client, self.plan, [])
        with self.assertRaises(ValueError):
            fetch_basket_snapshot(self.client, self.plan, [{'product_name': '可乐'}])

    def test_store_code_and_channel_are_validated_by_order_context(self):
        bad = {'store': {'code': 'abc'}, 'fulfillment': {'channel': 'pickup'}}
        with self.assertRaises(ValueError):
            fetch_basket_snapshot(self.client, bad, [{'product_code': '9900008751'}])


class CliEntry(unittest.TestCase):
    def test_any_flag_runs_and_labels_no_budget(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = demo.main(['--any'])
        self.assertEqual(code, 0, err.getvalue())
        self.assertIn('未设预算', out.getvalue())

    def test_default_still_uses_budget(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = demo.main([])
        self.assertEqual(code, 0, err.getvalue())
        self.assertIn('预算 ¥35.00', out.getvalue())


class PayloadShapes(unittest.TestCase):
    def setUp(self):
        self.inner = json.loads((ROOT / 'fixtures/order-history-sample.json').read_text())['payload']

    def test_accepts_business_envelope(self):
        self.assertEqual(len(order_history(self.inner)), 1)

    def test_accepts_direct_list_shape(self):
        self.assertEqual(len(order_history({'list': self.inner['data']['list']})), 1)

    def test_accepts_mcp_result_wrapper(self):
        wrapped = {'content': [{'type': 'text', 'text': '## Original Response\n' + json.dumps(self.inner, ensure_ascii=False)}]}
        self.assertIsNotNone(tool_payload(wrapped))
        self.assertEqual(len(order_history(wrapped)), 1)

    def test_accepts_structured_content(self):
        self.assertEqual(len(order_history({'structuredContent': self.inner})), 1)

    def test_whitelist_allows_read_only_history(self):
        self.assertIn('order-list', READ_TOOLS)
        for write_tool in ('create-order', 'cancel-order', 'auto-bind-coupons', 'mall-create-order', 'draw-lottery'):
            self.assertNotIn(write_tool, READ_TOOLS)


class AvailableBasket(unittest.TestCase):
    def setUp(self):
        self.plan = {'store': {'code': '1990001', 'name': '演示门店'}, 'fulfillment': {'channel': 'pickup'}}
        self.client = Mock()
        def call(name, args=None):
            code = args['items'][0]['productCode']
            if code == 'SOLD-OUT':
                raise MCPError('商品已售罄或不可售')
            if code == 'COMBO-INTERNAL':
                return {'price': 0}
            return {'price': 950}
        self.client.call.side_effect = call

    def test_drops_unavailable_and_internal_items_without_substitution(self):
        items = [{'product_code': 'COLA', 'product_name': '可乐'},
                 {'product_code': 'SOLD-OUT', 'product_name': '下架商品'},
                 {'product_code': 'COMBO-INTERNAL', 'product_name': '套餐内部件'}]
        kept, dropped = available_basket(self.client, self.plan, items)
        self.assertEqual([i['product_code'] for i in kept], ['COLA'])
        self.assertEqual({d['item']['product_code'] for d in dropped}, {'SOLD-OUT', 'COMBO-INTERNAL'})
        self.assertIn('不能单独点', next(d['reason'] for d in dropped if d['item']['product_code'] == 'COMBO-INTERNAL'))

    def test_all_dropped_leaves_empty_basket(self):
        kept, dropped = available_basket(self.client, self.plan, [{'product_code': 'SOLD-OUT'}])
        self.assertEqual(kept, [])
        self.assertEqual(len(dropped), 1)


class SeparateScenarios(unittest.TestCase):
    """企业团餐与派对不是个人点餐的渠道，必须显式拒绝而不是混用参数。"""

    def test_group_and_party_are_rejected_with_named_reason(self):
        from gourmet.channels import SEPARATE_SCENARIOS, order_context
        for channel, label in SEPARATE_SCENARIOS.items():
            with self.assertRaises(ValueError) as ctx:
                order_context({'store': {'code': '1990001'}, 'fulfillment': {'channel': channel}})
            self.assertIn(label, str(ctx.exception))

    def test_personal_channels_still_work(self):
        from gourmet.channels import order_context
        base = order_context({'store': {'code': '1990001'}, 'fulfillment': {'channel': 'pickup'}})
        self.assertEqual(base, {'storeCode': '1990001', 'beType': 1, 'orderType': 1})


if __name__ == '__main__':
    unittest.main()
