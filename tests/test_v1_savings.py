"""v1 · P0-2：可核验的省钱数字（基线必须同店、来源明确、可复算）。"""

import json
import unittest
from pathlib import Path

from gourmet.core import review

ROOT = Path(__file__).resolve().parents[1]


class Savings(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'fixtures/snapshot.json').read_text())
        self.store = self.data['store']['code']
        self.prices = {p['id']: p['price_cents'] for p in self.data['plans']}

    def price_of(self, plan_id):
        return self.prices[plan_id]

    # ---- 基线来自本店候选（推荐路径）----
    def test_baseline_from_plan_computes_savings(self):
        baseline_id = max(self.prices, key=lambda k: self.prices[k])   # 最贵的一份当"你本来会点的"
        result = review(self.data, taste='spicy', baseline_plan_id=baseline_id)
        self.assertEqual(result['baseline']['kind'], 'plan')
        self.assertEqual(result['baseline']['plan_id'], baseline_id)
        self.assertEqual(result['baseline']['price_cents'], self.price_of(baseline_id))
        self.assertEqual(result['baseline']['store_code'], self.store)
        base_price = self.price_of(baseline_id)
        for plan in result['plans']:
            expected = base_price - self.price_of(plan['id'])
            self.assertEqual(plan['saving_cents'], expected)
            self.assertEqual(plan['saving_percent'], round(100.0 * expected / base_price, 1))

    def test_baseline_plan_itself_saves_nothing(self):
        baseline_id = sorted(self.prices)[0]
        result = review(self.data, baseline_plan_id=baseline_id)
        base = next(p for p in result['plans'] if p['id'] == baseline_id)
        self.assertEqual(base['saving_cents'], 0)
        self.assertEqual(base['saving_percent'], 0.0)

    def test_best_saving_points_at_largest_positive_saving(self):
        baseline_id = max(self.prices, key=lambda k: self.prices[k])
        result = review(self.data, taste='spicy', baseline_plan_id=baseline_id)
        best = result['best_saving']
        self.assertIsNotNone(best)
        eligible = [p for p in result['plans'] if p['eligible']]
        self.assertEqual(best['saving_cents'], max(p['saving_cents'] for p in eligible))
        target = next(p for p in eligible if p['id'] == best['plan_id'])
        self.assertEqual(target['saving_cents'], best['saving_cents'])

    def test_negative_savings_are_recorded_but_never_best(self):
        baseline_id = min(self.prices, key=lambda k: self.prices[k])   # 最便宜的一份当基线
        result = review(self.data, baseline_plan_id=baseline_id)
        self.assertTrue(any(p['saving_cents'] < 0 for p in result['plans']))
        self.assertIsNone(result['best_saving'])

    # ---- 基线来自外部真实核价 ----
    def test_external_quote_requires_same_store(self):
        ok = review(self.data, baseline_cents=4850, baseline_store_code=self.store, baseline_label='单品直选')
        self.assertEqual(ok['baseline']['kind'], 'quote')
        self.assertEqual(ok['baseline']['price_cents'], 4850)
        self.assertEqual(ok['baseline']['label'], '单品直选')
        with self.assertRaises(ValueError):
            review(self.data, baseline_cents=4850)                      # 缺门店
        with self.assertRaises(ValueError):
            review(self.data, baseline_cents=4850, baseline_store_code='9999999')  # 跨店

    def test_external_quote_must_be_positive_int(self):
        for bad in (0, -1, 4850.0, '4850', None):
            if bad is None:
                continue
            with self.assertRaises(ValueError):
                review(self.data, baseline_cents=bad, baseline_store_code=self.store)

    # ---- 参数互斥与来源检查 ----
    def test_ambiguous_baseline_rejected(self):
        with self.assertRaises(ValueError):
            review(self.data, baseline_plan_id='cheese-corn', baseline_cents=4850, baseline_store_code=self.store)

    def test_unknown_baseline_plan_rejected(self):
        with self.assertRaises(ValueError):
            review(self.data, baseline_plan_id='not-a-plan')

    def test_label_without_price_rejected(self):
        with self.assertRaises(ValueError):
            review(self.data, baseline_label='单品直选')
        with self.assertRaises(ValueError):
            review(self.data, baseline_store_code=self.store)

    # ---- 没有基线时保持干净 ----
    def test_without_baseline_outputs_are_none(self):
        result = review(self.data)
        self.assertIsNone(result['baseline'])
        self.assertIsNone(result['best_saving'])
        self.assertTrue(all('saving_cents' not in p for p in result['plans']))

    # ---- 确定性 ----
    def test_baseline_is_idempotent_and_changes_review_id(self):
        a = review(self.data, baseline_plan_id='chicken-classic')
        b = review(self.data, baseline_plan_id='chicken-classic')
        c = review(self.data)
        self.assertEqual(a['review_id'], b['review_id'])
        self.assertNotEqual(a['review_id'], c['review_id'])


class RealCapture(unittest.TestCase):
    """用 2026-10-17 官方 MCP 实拍快照验证省钱数字（离线、可复算）。"""

    def setUp(self):
        self.data = json.loads((ROOT / 'fixtures/hongwu-single-vs-combo.json').read_text())

    def test_fixture_is_honest_snapshot(self):
        self.assertEqual(self.data['mode'], 'snapshot')
        self.assertNotIn('live', self.data['mode'])
        # 单件独立核价之和必须等于单品直选报价——否则基线篮子混入了非单点商品
        per_item = self.data['evidence']['per_item_cents']
        base = self.data['evidence']['single_pick_cents']
        self.assertEqual(per_item['1100'] + per_item['4810'] + per_item['9900008751'], base)
        # 套餐内部 SKU 单独核价为 0：这正是"不能拿它拼基线"的证据
        self.assertEqual(per_item['3050'], 0)

    def test_combo_saves_12_yuan_off_single_pick(self):
        result = review(self.data, budget_cents=5000, baseline_plan_id='single-pick')
        self.assertEqual(result['baseline']['price_cents'], 4850)
        combo = next(p for p in result['plans'] if p['id'] == 'combo-3pc')
        self.assertEqual(combo['price_cents'], 3650)
        self.assertEqual(combo['saving_cents'], 1200)
        self.assertEqual(combo['saving_percent'], 24.7)
        self.assertEqual(result['best_saving']['plan_id'], 'combo-3pc')
        single = next(p for p in result['plans'] if p['id'] == 'single-pick')
        self.assertEqual(single['saving_cents'], 0)

    def test_combo_is_not_cheapest_by_accident_of_unknown_nutrition(self):
        # 两份营养都未知：未知不得当作 0，也不得因此产生"更健康"的结论
        result = review(self.data, budget_cents=5000, baseline_plan_id='single-pick')
        self.assertTrue(all(p['sodium_mg'] is None for p in result['plans']))
        self.assertEqual(result['tradeoffs']['price_sodium'], [])
        self.assertEqual(result['tradeoffs']['nutrition_multi'], [])


if __name__ == '__main__':
    unittest.main()
