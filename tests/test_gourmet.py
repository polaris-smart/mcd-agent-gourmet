import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock
from gourmet.core import money_to_cents, review, select_plan
from gourmet.live import assemble, nutrition_rows, quoted_cents, fetch_snapshot
from gourmet.mcp import Client, MCPError, decode_message, tool_data

ROOT = Path(__file__).resolve().parents[1]
class Decisions(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'fixtures/snapshot.json').read_text())
    def test_three_distinct_opinions(self):
        r=review(self.data,3500,'spicy')
        self.assertEqual(r['reviewers'],{'budget':'cheese-corn','nutrition':'fish-corn','taste':'chicken-corn'})
        self.assertTrue(r['disagreement'])
    def test_drink_is_not_a_meal(self):
        p=self.data['plans'][0];p['items']=[i for i in p['items'] if i['kind']=='drink'];p['price_cents']=1
        r=review(self.data)
        self.assertFalse(r['plans'][0]['eligible']);self.assertNotIn(p['id'],r['reviewers'].values())
    def test_missing_nutrition_is_not_zero(self):
        p=self.data['plans'][0];p['sodium_mg']=None;p['energy_kcal']=None
        r=review(self.data,sodium_limit=1500)
        self.assertFalse(r['plans'][0]['eligible']);self.assertIsNone(r['plans'][0]['sodium_mg'])
    def test_unknown_cannot_win_nutrition(self):
        for p in self.data['plans']:p['sodium_mg']=None
        self.assertIsNone(review(self.data)['reviewers']['nutrition'])
    def test_no_meal_in_budget(self):
        r=review(self.data,3000);self.assertEqual(r['feasible_count'],0)
        self.assertTrue(all(x is None for x in r['reviewers'].values()))
    def test_exclusion_is_hard(self):
        r=review(self.data,5000,'no-spicy');self.assertTrue(all(not p['eligible'] for p in r['plans'] if p['spicy']))
    def test_fries_requirement(self):
        r=review(self.data,5000,side='fries');self.assertEqual(r['feasible_count'],3)
        self.assertTrue(all('classic' in p['id'] for p in r['plans'] if p['eligible']))
    def test_unknown_spice_is_excluded(self):
        self.data['plans'][0]['spicy']=None
        self.assertFalse(review(self.data,taste='no-spicy')['plans'][0]['eligible'])
    def test_expired_live_quote_cannot_select(self):
        self.data['mode']='live';self.data['captured_at']=(datetime.now(timezone.utc)-timedelta(minutes=16)).isoformat()
        r=review(self.data);self.assertEqual(r['feasible_count'],0)
        with self.assertRaises(ValueError):select_plan(r,'cheese-corn',r['review_id'])
    def test_future_quote_rejected(self):
        self.data['mode']='live';self.data['captured_at']=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        self.assertEqual(review(self.data)['feasible_count'],0)
    def test_selection_invalidated_by_requirements(self):
        a=review(self.data,3500);b=review(self.data,3000)
        with self.assertRaises(ValueError):select_plan(b,'cheese-corn',a['review_id'])
    def test_select_does_not_order(self):
        r=review(self.data);s=select_plan(r,'cheese-corn',r['review_id'])
        self.assertEqual(s['status'],'selected_not_ordered')
    def test_money_exact_and_invalid(self):
        self.assertEqual(money_to_cents('33.50'),3350)
        for v in ['NaN','Infinity','-1','1.001','0','10001','abc']:
            with self.subTest(v=v),self.assertRaises(ValueError):money_to_cents(v)
    def test_cross_store_rejected(self):
        self.data['plans'][0]['store_code']='other'
        with self.assertRaises(ValueError):review(self.data)
    def test_invalid_price_rejected(self):
        for v in [True,33.5,None,-1]:
            d=copy.deepcopy(self.data);d['plans'][0]['price_cents']=v
            with self.subTest(v=v),self.assertRaises(ValueError):review(d)
    def test_no_fake_balance_claim(self):
        self.assertNotIn('营养均衡',json.dumps(review(self.data),ensure_ascii=False))

class MCPContract(unittest.TestCase):
    def test_tool_write_blocked_before_network(self):
        c=Client('local-test-placeholder');c.request=Mock()
        for name in ['create-order','auto-bind-coupons','draw-lottery']:
            with self.assertRaises(MCPError):c.call(name,{})
        c.request.assert_not_called()
    def test_rpc_id_and_sse(self):
        raw='event: message\ndata: {"jsonrpc":"2.0","method":"notice"}\n\ndata: {"jsonrpc":"2.0","id":3,"result":{"ok":true}}\n\n'
        self.assertEqual(decode_message(raw,'text/event-stream',3)['result'],{'ok':True})
        with self.assertRaises(MCPError):decode_message('{"id":2,"result":{}}','application/json',1)
    def test_business_errors_not_data(self):
        for r in [{'isError':True},{'structuredContent':{'code':600012,'data':{}}},{'structuredContent':{'success':False}}]:
            with self.assertRaises(MCPError):tool_data(r)
    def test_text_and_structured_parsing(self):
        self.assertEqual(tool_data({'content':[{'type':'text','text':'{"code":0,"data":{"price":3200}}'}]}),{'price':3200})
    def test_price_not_menu_fallback(self):
        self.assertEqual(quoted_cents({'price':3200}),3200)
        for r in [{'currentPrice':'32'},{'price':'3200'},{'price':-1}]:
            with self.assertRaises(MCPError):quoted_cents(r)
    def test_nutrition_toon_and_unknown(self):
        n=nutrition_rows('[1]{productName,energyKcal,sodium,protein}:\n  示例,200,null,8')
        self.assertIsNone(n['示例']['sodium_mg']);self.assertEqual(n['示例']['energy_kcal'],200)
    def test_changed_combo_rejected(self):
        with self.assertRaises(MCPError):assemble({'rounds':[]},{})
    def test_failure_stops_without_demo(self):
        c=Mock();c.call.side_effect=MCPError('offline')
        plan=json.loads((ROOT/'fixtures/plan.json').read_text())
        with self.assertRaises(MCPError):fetch_snapshot(c,plan)
        self.assertEqual(c.call.call_count,1)

if __name__=='__main__':unittest.main()
