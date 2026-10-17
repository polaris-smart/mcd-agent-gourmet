"""v0.4：前沿解释（被谁支配）与预算阶梯。"""

import copy
import json
import unittest
from pathlib import Path

from gourmet.core import budget_ladder, review, tradeoff_candidates, tradeoff_reasons

ROOT = Path(__file__).resolve().parents[1]


class TradeoffReasons(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'fixtures/snapshot.json').read_text())

    def test_frontier_matches_candidates(self):
        plans = review(self.data, taste='spicy')['plans']
        candidates = tradeoff_candidates(plans)
        for name, report in tradeoff_reasons(plans).items():
            self.assertEqual(report['frontier'], candidates[name], name)
            self.assertEqual(len(report['frontier']), len(set(report['frontier'])), name)

    def test_every_dominated_plan_names_a_real_dominator_with_a_reason(self):
        plans = review(self.data, taste='spicy')['plans']
        by_id = {p['id']: p for p in plans}
        reports = tradeoff_reasons(plans)
        for name, report in reports.items():
            self.assertTrue(report['dominated'], name)
            for plan_id, info in report['dominated'].items():
                self.assertIn(info['by'], by_id)
                self.assertNotEqual(info['by'], plan_id)
                self.assertTrue(info['why'], (name, plan_id))
                self.assertNotIn(plan_id, report['frontier'])

    def test_equal_candidates_are_not_reported_as_dominated(self):
        plan = copy.deepcopy(self.data['plans'][-1])
        plan['id'] = 'equal-fish'
        self.data['plans'].append(plan)
        plans = review(self.data, taste='spicy')['plans']
        report = tradeoff_reasons(plans)['price_sodium']
        self.assertIn('equal-fish', report['frontier'])
        self.assertNotIn('equal-fish', report['dominated'])

    def test_missing_sodium_is_excluded_not_scored(self):
        for p in self.data['plans']:
            p['sodium_mg'] = None
        plans = review(self.data)['plans']
        report = tradeoff_reasons(plans)['price_sodium']
        self.assertEqual(report['frontier'], [])
        self.assertEqual(report['excluded_incomplete'], sorted(p['id'] for p in plans if p['eligible']))

    def test_reasons_are_deterministic(self):
        first = review(self.data, taste='spicy')['tradeoff_reasons']
        second = review(self.data, taste='spicy')['tradeoff_reasons']
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))


class BudgetLadder(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'fixtures/snapshot.json').read_text())

    def test_ladder_steps_for_infeasible_budget(self):
        plans = review(self.data, budget_cents=3000, taste='spicy')['plans']
        ladder = budget_ladder(plans, 3000)
        self.assertEqual(ladder['needed_cents'], 3200)
        self.assertEqual([s['budget_cents'] for s in ladder['steps']], [3200, 3250, 3350])
        self.assertEqual([s['candidates'] for s in ladder['steps']], [2, 3, 5])
        self.assertEqual([s['increase_cents'] for s in ladder['steps']], [200, 250, 350])

    def test_ladder_is_empty_when_something_is_feasible(self):
        plans = review(self.data, budget_cents=3500, taste='spicy')['plans']
        self.assertEqual(budget_ladder(plans, 3500), {'needed_cents': None, 'steps': []})

    def test_ladder_is_empty_when_blocked_by_other_conditions(self):
        # 把饮料含糖信息全部置为未知：此时每份候选都同时有非预算原因，
        # 提高预算并不能解决，阶梯必须为空（不放宽其他条件）。
        for p in self.data['plans']:
            for item in p['items']:
                if item['kind'] == 'drink':
                    item['sugar'] = None
        plans = review(self.data, budget_cents=3000, sugar='zero')['plans']
        self.assertFalse(any(p['eligible'] for p in plans))
        self.assertTrue(all(len(p['reasons']) > 1 for p in plans))
        self.assertEqual(budget_ladder(plans, 3000), {'needed_cents': None, 'steps': []})

    def test_ladder_never_relaxes_other_conditions(self):
        plans = review(self.data, budget_cents=3000, taste='spicy', side='fries')['plans']
        ladder = budget_ladder(plans, 3000)
        for step in ladder['steps']:
            eligible_at = [p for p in plans
                           if p['price_cents'] <= step['budget_cents']
                           and all(r.startswith('超预算') for r in p['reasons'])]
            self.assertEqual(len(eligible_at), step['candidates'])

    def test_review_exposes_both_reports(self):
        result = review(self.data, budget_cents=3000, taste='spicy')
        self.assertIn('tradeoff_reasons', result)
        self.assertIn('budget_ladder', result)
        self.assertEqual(result['budget_ladder']['needed_cents'], 3200)
        self.assertEqual(result['review_id'], review(self.data, budget_cents=3000, taste='spicy')['review_id'])


if __name__ == '__main__':
    unittest.main()
