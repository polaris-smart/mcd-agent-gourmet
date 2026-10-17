"""v1 · P1-1：首屏一个答案 + 一句可核对理由 + 可复制点单卡。"""

import copy
import json
import unittest
from pathlib import Path

from gourmet.core import default_pick, order_card, pick_reason, review

ROOT = Path(__file__).resolve().parents[1]


class DefaultPick(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'fixtures/snapshot.json').read_text())

    def test_without_baseline_picks_cheapest_eligible(self):
        result = review(self.data, budget_cents=5000)
        pick = default_pick(result)
        eligible = [p for p in result['plans'] if p['eligible']]
        self.assertEqual(pick['price_cents'], min(p['price_cents'] for p in eligible))
        self.assertTrue(pick['eligible'])

    def test_with_baseline_picks_biggest_saving(self):
        baseline_id = max((p['id'] for p in self.data['plans']),
                          key=lambda pid: next(p['price_cents'] for p in self.data['plans'] if p['id'] == pid))
        result = review(self.data, budget_cents=5000, baseline_plan_id=baseline_id)
        pick = default_pick(result)
        eligible = [p for p in result['plans'] if p['eligible']]
        self.assertEqual(pick['saving_cents'], max(p['saving_cents'] for p in eligible))

    def test_no_eligible_means_no_pick(self):
        self.assertIsNone(default_pick(review(self.data, budget_cents=1000)))


class PickReason(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'fixtures/snapshot.json').read_text())

    def test_reason_mentions_saving_when_baseline_given(self):
        baseline_id = 'fish-classic'
        result = review(self.data, budget_cents=5000, baseline_plan_id=baseline_id)
        reason = pick_reason(result, 'cheese-corn')
        self.assertIn('省 ¥', reason)

    def test_reason_mentions_lowest_price_only_for_the_cheapest(self):
        result = review(self.data, budget_cents=5000)
        cheapest = sorted((p for p in result['plans'] if p['eligible']), key=lambda p: (p['price_cents'], p['id']))[0]
        self.assertIn('价格最低', pick_reason(result, cheapest['id']))

    def test_reason_mentions_lowest_sodium_only_when_true(self):
        result = review(self.data, budget_cents=5000)
        known = [p for p in result['plans'] if p['eligible'] and p['sodium_mg'] is not None]
        lowest = sorted(known, key=lambda p: (p['sodium_mg'], p['price_cents'], p['id']))[0]
        if lowest['id'] != sorted((p for p in result['plans'] if p['eligible']), key=lambda p: (p['price_cents'], p['id']))[0]['id']:
            self.assertIn('钠最低', pick_reason(result, lowest['id']))

    def test_reason_refuses_ineligible_or_unknown(self):
        result = review(self.data, budget_cents=1000)
        with self.assertRaises(ValueError):
            pick_reason(result, result['plans'][0]['id'])
        with self.assertRaises(ValueError):
            pick_reason(result, 'not-a-plan')


class OrderCard(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'fixtures/snapshot.json').read_text())

    def test_card_carries_store_items_total_and_disclaimer(self):
        result = review(self.data, budget_cents=5000)
        card = order_card(result)
        self.assertEqual(card['status'], 'selected_not_ordered')
        self.assertIn(result['store']['name'], card['text'])
        self.assertIn('合计：', card['text'])
        self.assertIn('没有下单、没有支付', card['text'])
        for item in next(p for p in result['plans'] if p['id'] == card['plan_id'])['items']:
            self.assertIn(item['name'], card['text'])

    def test_card_includes_saving_line_when_baseline_present(self):
        result = review(self.data, budget_cents=5000, baseline_plan_id='fish-classic')
        card = order_card(result, 'cheese-corn')
        self.assertIn('比「', card['text'])
        self.assertIn('省 ¥', card['text'])

    def test_card_shows_per_person_for_groups(self):
        data = copy.deepcopy(self.data)
        base = data['plans'][0]
        duo = copy.deepcopy(base)
        duo['id'] = 'duo'
        duo['items'] = [copy.deepcopy(i) for i in base['items'] for _ in range(2)]
        duo['price_cents'] = 4000
        data['plans'].append(duo)
        result = review(data, budget_cents=5000, people=2)
        card = order_card(result, 'duo')
        self.assertIn('人均 ¥', card['text'])

    def test_card_passes_through_display_price_note(self):
        data = copy.deepcopy(self.data)
        data['plans'][0]['display_price_note'] = '菜单展示价 ¥32.00 附带条件「需随单购买麦金卡」；以核价 ¥58.50 为准。'
        result = review(data, budget_cents=5000)
        card = order_card(result, data['plans'][0]['id'])
        self.assertIn('菜单展示价 ¥32.00', card['text'])

    def test_card_refuses_when_nothing_fits(self):
        with self.assertRaises(ValueError):
            order_card(review(self.data, budget_cents=1000))
        result = review(self.data, budget_cents=1000)
        with self.assertRaises(ValueError):
            order_card(result, result['plans'][0]['id'])


if __name__ == '__main__':
    unittest.main()
