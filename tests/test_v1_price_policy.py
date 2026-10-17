"""v1 · P0-3：菜单展示价污染防护（条件价必须标注，金额只认核价）。"""

import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from gourmet.live import DISPLAY_PRICE_CONDITIONS, display_price_report, fetch_snapshot, price_text_to_cents

ROOT = Path(__file__).resolve().parents[1]


class PriceText(unittest.TestCase):
    def test_parses_yuan_strings(self):
        self.assertEqual(price_text_to_cents('¥32.00'), 3200)
        self.assertEqual(price_text_to_cents('32'), 3200)
        self.assertEqual(price_text_to_cents('58.5'), 5850)
        self.assertEqual(price_text_to_cents(' ￥1,234.50 '), 123450)

    def test_refuses_to_guess(self):
        for bad in ('元', '', '约32', '32元起', None, 32, 32.0, '3 2'):
            self.assertIsNone(price_text_to_cents(bad), bad)


class DisplayPriceReport(unittest.TestCase):
    def test_no_condition_and_matching_price_is_silent(self):
        report = display_price_report({'currentPrice': '36.5'}, 3650)
        self.assertEqual(report, {'display_price_cents': 3650, 'display_price_condition': None, 'display_price_note': None})

    def test_conditional_price_below_quote_explains_the_gap(self):
        item = {'currentPrice': '32', 'originalPrice': '58.5', 'discountType': '随单购麦金卡优惠'}
        report = display_price_report(item, 5850)
        self.assertEqual(report['display_price_cents'], 3200)
        self.assertEqual(report['display_price_condition'], '需随单购买麦金卡')
        self.assertIn('菜单展示价 ¥32.00', report['display_price_note'])
        self.assertIn('实际核价 ¥58.50', report['display_price_note'])
        self.assertIn('只有核价才是你要付的钱', report['display_price_note'])

    def test_every_known_condition_maps_to_a_readable_phrase(self):
        for raw, phrase in DISPLAY_PRICE_CONDITIONS.items():
            report = display_price_report({'currentPrice': '10', 'discountType': raw}, 1000)
            self.assertEqual(report['display_price_condition'], phrase)

    def test_unknown_condition_is_not_invented(self):
        report = display_price_report({'currentPrice': '10', 'discountType': '未来新模式优惠'}, 1000)
        self.assertIsNone(report['display_price_condition'])

    def test_can_with_order_fallback(self):
        report = display_price_report({'currentPrice': '32', 'canWithOrder': True}, 3200)
        self.assertIn('随单购', report['display_price_condition'])
        self.assertIn('以核价 ¥32.00 为准', report['display_price_note'])

    def test_plain_mismatch_is_flagged(self):
        report = display_price_report({'currentPrice': '39'}, 3650)
        self.assertIsNone(report['display_price_condition'])
        self.assertIn('不一致', report['display_price_note'])

    def test_unparsable_price_never_produces_a_note(self):
        report = display_price_report({'currentPrice': '元'}, 3650)
        self.assertIsNone(report['display_price_cents'])
        self.assertIsNone(report['display_price_note'])


class LiveSnapshot(unittest.TestCase):
    """真实形状的假响应：菜单写 ¥32，核价是 ¥58.50，必须被标出来。"""

    def setUp(self):
        self.menu_code = '9900000888'
        self.responses = {
            'query-meals': {'meals': {self.menu_code: {
                'name': '巨无霸四件套', 'currentPrice': '32', 'originalPrice': '58.5',
                'discountType': '随单购麦金卡优惠', 'canWithOrder': True}}},
            'list-nutrition-foods': [
                {'productName': '巨无霸', 'energyKcal': '500', 'sodium': '900', 'protein': '25'},
                {'productName': '中薯条', 'energyKcal': '300', 'sodium': '200', 'protein': '3'},
                {'productName': '可乐中杯', 'energyKcal': '150', 'sodium': '20', 'protein': '0'},
            ],
            'query-meal-detail': {'code': self.menu_code, 'name': '巨无霸四件套', 'rounds': [
                {'id': 1, 'name': '主', 'minQuantity': 1, 'maxQuantity': 1,
                 'choices': [{'code': '1120', 'name': '巨无霸', 'isDefault': 1, 'quantity': 1}]},
                {'id': 2, 'name': '小食', 'minQuantity': 1, 'maxQuantity': 1,
                 'choices': [{'code': '4810', 'name': '中薯条', 'isDefault': 1, 'quantity': 1}]},
                {'id': 3, 'name': '饮料', 'minQuantity': 1, 'maxQuantity': 1,
                 'choices': [{'code': '3050', 'name': '可乐中杯', 'isDefault': 1, 'quantity': 1}]},
            ]},
            'calculate-price': {'price': 5850, 'takeWayList': [{'code': 'take-in-store', 'title': '外带', 'subtitle': '店内自提'}]},
        }
        self.client = Mock()
        self.client.call.side_effect = lambda name, args=None: self.responses[name]
        self.plan = {'store': {'code': '1990001', 'name': '演示门店'},
                     'fulfillment': {'channel': 'pickup'},
                     'candidates': [{'id': 'four-pc', 'product_code': self.menu_code, 'label': '巨无霸四件套', 'spicy': False}]}

    def test_price_comes_from_quote_not_menu_display(self):
        snap = fetch_snapshot(self.client, self.plan)
        plan = snap['plans'][0]
        self.assertEqual(plan['price_cents'], 5850)                 # 核价
        self.assertEqual(plan['display_price_cents'], 3200)         # 菜单展示价
        self.assertEqual(plan['display_price_condition'], '需随单购买麦金卡')
        self.assertIn('实际核价 ¥58.50', plan['display_price_note'])

    def test_snapshot_declares_price_policy(self):
        snap = fetch_snapshot(self.client, self.plan)
        self.assertIn('calculate-price', snap['price_policy'])
        self.assertEqual(snap['mode'], 'live')


if __name__ == '__main__':
    unittest.main()
