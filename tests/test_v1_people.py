"""v1 · P0-1：人数作为一等输入（份数完备性、人均、预算口径）。"""

import copy
import json
import unittest
from pathlib import Path

from gourmet.core import review

ROOT = Path(__file__).resolve().parents[1]


def duo_plan(base, price_cents=5290):
    """由单人餐模板拼出一份双人餐：2 主食 + 2 小食 + 2 饮料。"""
    plan = copy.deepcopy(base)
    plan['id'] = 'duo-share'
    plan['name'] = '全明星双人分享餐八件套'
    items = []
    for kind in ('main', 'side', 'drink'):
        source = next(i for i in base['items'] if i['kind'] == kind)
        for _ in range(2):
            item = copy.deepcopy(source)
            item['quantity'] = 1
            items.append(item)
    plan['items'] = items
    plan['price_cents'] = price_cents
    return plan


class People(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'fixtures/snapshot.json').read_text())

    def with_duo(self, price_cents=5290):
        self.data['plans'].append(duo_plan(self.data['plans'][0], price_cents))

    # ---- 向后兼容 ----
    def test_default_is_unchanged(self):
        base = review(self.data, taste='spicy')
        explicit = review(self.data, taste='spicy', people=1, budget_scope='total')
        self.assertEqual(base['tradeoffs'], explicit['tradeoffs'])
        self.assertEqual(base['feasible_count'], explicit['feasible_count'])
        self.assertEqual([p['eligible'] for p in base['plans']], [p['eligible'] for p in explicit['plans']])
        self.assertEqual(base['review_id'], explicit['review_id'])

    # ---- 参数校验 ----
    def test_people_must_be_int_in_range(self):
        for bad in (0, 9, -1, '2', 2.0, None):
            with self.assertRaises(ValueError):
                review(self.data, people=bad)

    def test_budget_scope_must_be_known(self):
        with self.assertRaises(ValueError):
            review(self.data, budget_scope='per-head')

    # ---- 份数完备性 ----
    def test_two_people_rejects_single_meal_with_reason(self):
        result = review(self.data, taste='spicy', people=2)
        self.assertEqual(result['feasible_count'], 0)
        reason = result['plans'][0]['reasons'][0]
        self.assertIn('2 人份', reason)
        self.assertIn('主食 1/2', reason)
        self.assertIn('饮料 1/2', reason)

    def test_two_people_accepts_duo(self):
        self.with_duo()
        result = review(self.data, budget_cents=6000, taste='spicy', people=2)
        duo = next(p for p in result['plans'] if p['id'] == 'duo-share')
        self.assertTrue(duo['eligible'], duo['reasons'])
        self.assertEqual(duo['structure'], 'share')
        self.assertEqual(result['feasible_count'], 1)

    def test_single_meal_labeled_single_structure(self):
        result = review(self.data, people=1)
        self.assertTrue(all(p['structure'] == 'single' for p in result['plans']))

    # ---- 人均与预算口径 ----
    def test_per_person_cents_is_ceil_and_exposed(self):
        self.with_duo(price_cents=5291)
        result = review(self.data, taste='spicy', people=2)
        duo = next(p for p in result['plans'] if p['id'] == 'duo-share')
        self.assertEqual(duo['per_person_cents'], 2646)  # 5291/2 向上取整
        self.assertEqual(result['requirements']['people'], 2)
        self.assertEqual(result['requirements']['effective_budget_cents'], 3500)

    def test_per_person_budget_scope_multiplies(self):
        self.with_duo(price_cents=5290)
        total = review(self.data, budget_cents=2650, taste='spicy', people=2, budget_scope='total')
        self.assertEqual(total['feasible_count'], 0)
        per_head = review(self.data, budget_cents=2650, taste='spicy', people=2, budget_scope='per_person')
        duo = next(p for p in per_head['plans'] if p['id'] == 'duo-share')
        self.assertTrue(duo['eligible'], duo['reasons'])
        self.assertEqual(per_head['requirements']['effective_budget_cents'], 5300)

    def test_budget_ladder_uses_effective_budget(self):
        # 2 人、人均 20 元（整单有效预算 ¥40）：单人餐因份数不足被排除，
        # 唯一"只差预算"的候选是双人餐 ¥52.90 → 阶梯应报整单口径。
        self.with_duo(price_cents=5290)
        result = review(self.data, budget_cents=2000, taste='spicy', people=2, budget_scope='per_person')
        ladder = result['budget_ladder']
        self.assertEqual(ladder['needed_cents'], 5290)
        self.assertEqual(ladder['steps'][0]['candidates'], 1)
        self.assertEqual(ladder['steps'][0]['increase_cents'], 1290)  # 5290 - 4000

    # ---- 不确定性 ----
    def test_review_id_depends_on_people(self):
        one = review(self.data, taste='spicy', people=1)['review_id']
        two = review(self.data, taste='spicy', people=2)['review_id']
        self.assertNotEqual(one, two)
        self.assertEqual(two, review(self.data, taste='spicy', people=2)['review_id'])


if __name__ == '__main__':
    unittest.main()
