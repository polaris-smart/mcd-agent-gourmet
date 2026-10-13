import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import Mock
import demo
from gourmet.core import review
from gourmet.live import coupon_choices, plan_with_coupon, fetch_snapshot, store_coupons
from gourmet.mcp import MCPError

ROOT = Path(__file__).resolve().parents[1]

class Tradeoffs(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'fixtures/snapshot.json').read_text())
    def test_two_actual_tradeoffs(self):
        r = review(self.data, taste='spicy')
        self.assertEqual(r['tradeoffs'], {'price_sodium':['cheese-corn','fish-corn'], 'taste_sodium':['chicken-corn','fish-corn'], 'nutrition_multi':['cheese-corn','fish-corn','cheese-classic','fish-classic']})
    def test_hard_constraints_and_missing_values(self):
        self.assertEqual(review(self.data, budget_cents=3000)['tradeoffs']['price_sodium'], [])
        for p in self.data['plans']: p['sodium_mg'] = None
        self.assertEqual(review(self.data)['tradeoffs'], {'price_sodium':[], 'taste_sodium':[], 'nutrition_multi':[]})
    def test_four_dimensions_reject_dominated_and_incomplete_candidates(self):
        base = copy.deepcopy(self.data['plans'][0])
        cases = [('a',2000,500,600,30), ('b',2000,600,650,20),
                 ('c',1900,700,700,40), ('missing',2100,400,None,40)]
        self.data['plans'] = [dict(copy.deepcopy(base), id=name, price_cents=price,
                                  sodium_mg=sodium, energy_kcal=energy, protein_g=protein)
                              for name,price,sodium,energy,protein in cases]
        result = review(self.data)['tradeoffs']
        # a dominates b at equal price; c trades lower price/more protein for
        # higher sodium/energy; missing energy must not enter the 4-D comparison.
        self.assertEqual(result['nutrition_multi'], ['c','a'])
        for ids in result.values():
            self.assertEqual(len(ids), len(set(ids)))
    def test_equal_candidates_remain(self):
        p = copy.deepcopy(self.data['plans'][-1]); p['id']='equal-fish'; self.data['plans'].append(p)
        self.assertIn('equal-fish', review(self.data)['tradeoffs']['price_sodium'])
        self.assertIn('fish-corn', review(self.data)['tradeoffs']['price_sodium'])
    def test_no_spicy_is_never_relaxed(self):
        r = review(self.data, taste='no-spicy', side='fries')
        self.assertEqual(r['tradeoffs']['price_sodium'], ['cheese-classic','fish-classic'])
        self.assertEqual(r['tradeoffs']['taste_sodium'], ['fish-classic'])
    def test_json_stdout_and_mode_stderr(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err): code = demo.main(['--json'])
        self.assertEqual(code, 0)
        self.assertIn('历史快照', json.loads(out.getvalue())['data_notice'])
        self.assertIn('--live', err.getvalue())
    def test_synthetic_is_never_relabelled_real_snapshot(self):
        self.data['mode']='synthetic'
        with tempfile.TemporaryDirectory() as directory:
            source, dest = Path(directory)/'input.json', Path(directory)/'output.json'
            source.write_text(json.dumps(self.data))
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = demo.main(['--input',str(source),'--save-snapshot',str(dest),'--json'])
            self.assertEqual(code, 0)
            self.assertIn('合成测试数据', err.getvalue())
            self.assertEqual(json.loads(dest.read_text())['mode'], 'synthetic')

class Coupons(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/'fixtures/plan.json').read_text())
        self.coupon={'title':'测试券', 'couponId':'private-id', 'couponCode':'private-code',
                     'products':[{'productCode':self.plan['candidates'][0]['product_code']}]}
    def test_display_never_contains_private_identifiers(self):
        result=coupon_choices([self.coupon], self.plan)
        self.assertIn('chicken-classic', result[0]['candidate_ids'])
        self.assertNotIn('private', json.dumps(result))
    def test_resolve_exact_title_without_mutating_plan(self):
        adjusted=plan_with_coupon(self.plan, [self.coupon], '测试券', 'chicken-classic')
        self.assertEqual(adjusted['candidates'][0]['coupon']['couponId'],'private-id')
        self.assertNotIn('coupon',self.plan['candidates'][0])
    def test_missing_ambiguous_and_mismatching_coupon_rejected(self):
        for coupons,title,candidate in [([], '测试券', 'chicken-classic'),
                ([self.coupon]*2, '测试券', 'chicken-classic'),
                ([self.coupon], '测试券', 'fish-corn')]:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                plan_with_coupon(self.plan,coupons,title,candidate)
    def test_missing_pair_rejected(self):
        del self.coupon['couponCode']
        with self.assertRaises(MCPError): plan_with_coupon(self.plan,[self.coupon],'测试券','chicken-classic')
    def test_plain_live_does_not_depend_on_coupon_service(self):
        c=Mock(); c.call.side_effect=MCPError('stop at menu')
        with self.assertRaises(MCPError): fetch_snapshot(c,self.plan)
        self.assertEqual(c.call.call_args.args[0], 'query-meals')
    def test_pair_flags_required_before_network(self):
        c=Mock()
        with self.assertRaises(ValueError): fetch_snapshot(c,self.plan,coupon_title='测试券')
        c.call.assert_not_called()
    def test_unknown_coupon_structure_stops(self):
        c=Mock();c.call.return_value={'unexpected':[]}
        with self.assertRaises(MCPError):store_coupons(c,self.plan)

if __name__=='__main__':unittest.main()
