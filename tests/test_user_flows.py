import copy
import io
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timedelta, timezone
import demo
from gourmet.core import review
from gourmet.live import assemble, fetch_snapshot
from gourmet.member import member_overview, points_detail
from gourmet.stores import search_stores
from gourmet.mcp import MCPError, Client

ROOT = Path(__file__).resolve().parents[1]

class Preferences(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'fixtures/snapshot.json').read_text())
    def test_unknown_drink_is_not_sugar_free(self):
        self.data['plans'][1]['items'][-1].pop('sugar')
        result=review(self.data,sugar='zero')
        self.assertFalse(result['plans'][1]['eligible'])
        self.assertEqual(sum(p['eligible'] for p in result['plans']),2)
    def test_nutrition_constraints_use_unknown_not_zero(self):
        self.data['plans'][1]['protein_g']=None
        r=review(self.data,energy_limit=700,protein_min=20)
        self.assertFalse(r['plans'][1]['eligible'])
        self.assertIn('蛋白质数据不完整',r['plans'][1]['reasons'][0])
        for p in r['plans']:
            if p['eligible']:self.assertLessEqual(p['energy_kcal'],700);self.assertGreaterEqual(p['protein_g'],20)
    def test_budget_hint_never_relaxes_taste_or_drink(self):
        r=review(self.data,budget_cents=3000,taste='no-spicy',sugar='zero')
        self.assertEqual(r['feasible_count'],0)
        self.assertIn('32.00',r['next_step'])
        r=review(self.data,budget_cents=3000,sugar='zero',side='fries')
        self.assertNotIn('最低需要',r['next_step'])
    def test_multi_nutrition_missing_is_excluded_and_equal_retained(self):
        self.data['plans'][-1]['protein_g']=None
        self.assertNotIn('fish-corn',review(self.data)['tradeoffs']['nutrition_multi'])
        p=copy.deepcopy(self.data['plans'][3]);p['id']='tie';self.data['plans'].append(p)
        self.assertIn('tie',review(self.data)['tradeoffs']['nutrition_multi'])
    def test_configured_freshness_and_invalid_values(self):
        self.data['mode']='live';now=datetime.now(timezone.utc)
        self.data['captured_at']=(now-timedelta(minutes=20)).isoformat()
        self.assertEqual(review(self.data,now=now)['feasible_count'],0)
        self.assertGreater(review(self.data,now=now,freshness_minutes=30)['feasible_count'],0)
        for kwargs in [{'freshness_minutes':0},{'protein_min':-1},{'energy_limit':True},{'sugar':'guess'}]:
            with self.assertRaises(ValueError):review(self.data,**kwargs)
    def test_live_requires_explicit_store_before_connecting(self):
        with patch('demo.Client') as client, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(demo.main(['--live']),2)
        client.assert_not_called()
    def test_snapshot_cannot_be_relabelled_to_another_store(self):
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(demo.main(['--store-code','123']),2)
            self.assertEqual(demo.main(['--expand']),2)

    def test_live_store_without_meal_never_loads_demo_candidates(self):
        with patch('demo.Client') as client, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(demo.main(['--live', '--store-code', '9000001']), 2)
        client.assert_not_called()

    def test_switching_plan_store_requires_fresh_meal_selection(self):
        with patch('demo.Client') as client, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(demo.main(['--live', '--plan', str(ROOT/'fixtures/plan.json'), '--store-code', '9000001']), 2)
        client.assert_not_called()

    def test_menu_search_uses_only_requested_store(self):
        c=Mock();c.call.return_value={'meals':{'new-code':{'name':'当前餐品'}}}
        out=io.StringIO()
        with patch('demo.Client',return_value=c), redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(demo.main(['--list-meals', '--store-code', '9000001']), 0)
        self.assertEqual(c.call.call_args.args, ('query-meals', {'storeCode':'9000001','beType':1,'orderType':1}))
        self.assertEqual(json.loads(out.getvalue())['meals'], [{'code':'new-code','name':'当前餐品'}])

    def test_switching_delivery_store_never_keeps_old_business_code(self):
        plan=json.loads((ROOT/'fixtures/plan.json').read_text())
        plan['fulfillment']={'channel':'delivery','be_code':'old-store-pair'}
        with patch('demo.Path.read_text',return_value=json.dumps(plan)), patch('demo.Client') as client, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(demo.main(['--live','--plan','unused.json','--store-code','9000001','--meal-code','123']),2)
        client.assert_not_called()

class LiveCombos(unittest.TestCase):
    def setUp(self):
        self.detail={'code':'meal','name':'测试三件套','rounds':[
            {'id':'1','minQuantity':1,'maxQuantity':1,'choices':[{'code':'1440','name':'主食','isDefault':True,'quantity':1}]},
            {'id':'2','minQuantity':1,'maxQuantity':1,'choices':[
                {'code':'4810','name':'重命名的小食','isDefault':True,'quantity':1},
                {'code':'4437','name':'玉米','quantity':0}]},
            {'id':'3','minQuantity':1,'maxQuantity':1,'choices':[
                {'code':'3050','name':'可乐','isDefault':True,'quantity':1},
                {'code':'3071','name':'无糖可乐','quantity':0}]}]}
        self.plan={'store':{'code':'1','name':'所选店'},'candidates':[{'id':'meal','product_code':'meal','label':'默认','spicy':False}]}
    def test_product_code_survives_name_change(self):
        _,items=assemble(self.detail,{})
        self.assertTrue(items[1]['is_fries']);self.assertEqual(items[-1]['sugar'],'regular')
    def test_three_rounds_do_not_prove_a_complete_meal(self):
        self.detail['rounds'][0]['choices'][0]['code']='3050'
        with self.assertRaises(MCPError):assemble(self.detail,{})
    def test_cartesian_combos_each_have_official_quote(self):
        def call(name,args):
            if name=='query-meals':return {'meals':{'meal':{}}}
            if name=='list-nutrition-foods':return []
            if name=='query-meal-detail':return self.detail
            if name=='calculate-price':return {'price':2300}
            self.fail(name)
        c=Mock();c.call.side_effect=call
        data=fetch_snapshot(c,self.plan,expand=True)
        self.assertEqual(len(data['plans']),4)
        self.assertTrue(any(p['items'][1]['is_fries'] and p['items'][2]['sugar']=='zero' for p in data['plans']))
        self.assertEqual(sum(x.args[0]=='calculate-price' for x in c.call.call_args_list),4)
        self.assertTrue(all(p['protein_g'] is None for p in data['plans']))
    def test_unknown_options_and_coupon_do_not_expand_silently(self):
        c=Mock()
        with self.assertRaises(ValueError):fetch_snapshot(c,self.plan,expand=True,coupon_title='券',coupon_candidate='meal')
        c.call.assert_not_called()

class MemberViews(unittest.TestCase):
    def test_member_redacts_identifiers_and_reports_partial_pages(self):
        def call(name,args):
            if name=='query-my-account':return {'accountId':'SECRET','availablePoint':'123','currentMouthExpirePoint':None}
            if name=='query-my-coupons':return {'coupons':[{'title':'示例','code':'SECRET','id':'SECRET'}], 'currentPage':int(args['page']),'totalCount':6,'totalPages':6}
            return [{'couponName':'示例待领取','couponId':'SECRET'}]
        c=Mock();c.call.side_effect=call
        r=member_overview(c)
        self.assertFalse(r['owned_complete']);self.assertEqual(len(r['owned_coupons']),5)
        self.assertNotIn('SECRET',json.dumps(r));self.assertIsNone(r['points']['currentMouthExpirePoint'])
    def test_inconsistent_page_stops(self):
        c=Mock();c.call.side_effect=[{}, {'coupons':[], 'totalCount':0,'totalPages':0,'currentPage':2}]
        with self.assertRaises(MCPError):member_overview(c)
    def test_points_two_stage_amounts_and_notice_kept(self):
        c=Mock();c.call.return_value={'spuId':1,'note':'兑换需知：测试，不解析。','skuList':[{'skuId':2,'points':'100','price':'0','extTradePrice':'5'}],'accountId':'SECRET'}
        r=points_detail(c,1)
        self.assertEqual(r['note'],c.call.return_value['note'])
        self.assertEqual(r['skuList'][0]['price'],'0');self.assertEqual(r['skuList'][0]['extTradePrice'],'5')
        self.assertNotIn('SECRET',json.dumps(r))
    def test_member_cannot_save_or_mix_actions(self):
        with patch('demo.Client') as client,redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(demo.main(['--member','--save-snapshot','should-not-exist.json']),2)
            self.assertEqual(demo.main(['--member','--list-coupons']),2)
        client.assert_not_called()
    def test_write_operations_stay_blocked(self):
        c=Client('test');c.request=Mock()
        for name in ['mall-create-order','auto-bind-coupons','create-order']:
            with self.assertRaises(MCPError):c.call(name,{})
        c.request.assert_not_called()
    def test_store_search_shows_all_reservation_options(self):
        options=[{'date':'2026-10-13','today':True,'reservationOptionText':'09:00–10:00'}, {'date':'2026-10-14','today':False,'reservationOptionText':'10:00–11:00'}]
        c=Mock();c.call.return_value=[{'storeCode':'123','storeName':'示例门店','address':'示例地址','reservation':True,'reservationTimeOptions':options,'accountId':'SECRET'}]
        r=search_stores(c,'南京','商场')
        self.assertEqual(r['stores'][0]['reservationTimeOptions'],options);self.assertNotIn('SECRET',json.dumps(r))
        self.assertEqual(c.call.call_args.args[1]['searchType'],2)
        with self.assertRaises(ValueError):search_stores(c,'','')


class Customizations(unittest.TestCase):
    def test_ice_uses_selected_key_not_item_code_alone(self):
        from gourmet.customize import modifications
        choice={'modification':{'items':[{'minValues':1,'maxValues':1,'values':[
            {'code':'same','name':'标准','selectedQuantity':1,'selectedKey':'default-key','minQuantity':0,'maxQuantity':1},
            {'code':'same','name':'去冰','selectedQuantity':0,'selectedKey':'no-ice-key','minQuantity':0,'maxQuantity':1}]}]}}
        payload,labels=modifications(choice,'none')
        self.assertEqual(payload,{'values':[{'code':'same','key':'no-ice-key','quantity':1}]})
        self.assertEqual(labels,['去冰'])
        with self.assertRaises(MCPError):modifications(choice,'less')
    def test_omitted_and_retained_ingredients_both_sent(self):
        from gourmet.customize import modifications
        values=[{'code':name,'name':name,'selectedQuantity':1,'selectedKey':'yes','unselectedKey':'no','minQuantity':0,'maxQuantity':1} for name in ['酱','菜']]
        payload,labels=modifications({'modification':{'items':[{'minValues':0,'maxValues':2,'values':values}]}},omit=['酱'])
        self.assertEqual(payload['values'],[{'code':'酱','key':'no','quantity':0},{'code':'菜','key':'yes','quantity':1}])
        self.assertEqual(labels,['去除酱'])
    def test_unknown_ice_is_not_confirmed(self):
        d=json.loads((ROOT/'fixtures/snapshot.json').read_text())
        self.assertEqual(review(d,ice='none')['feasible_count'],0)
    def test_channel_context_requires_correct_pair(self):
        from gourmet.channels import order_context
        p={'store':{'code':'1'}}
        self.assertEqual(order_context(p),{'storeCode':'1','orderType':1,'beType':1})
        for channel,be,order in [('drive',5,1),('delivery',2,2)]:
            p['fulfillment']={'channel':channel}
            with self.assertRaises(ValueError):order_context(p)
            p['fulfillment']['be_code']='pair'
            self.assertEqual(order_context(p),{'storeCode':'1','beType':be,'orderType':order,'beCode':'pair'})
        p['fulfillment']={'channel':'pickup','be_code':'pair'}
        with self.assertRaises(ValueError):order_context(p)
    def test_delivery_address_reference_survives_reordering_and_detects_changes(self):
        from gourmet.stores import address_choices,delivery_stores
        a={'addressId':'PRIVATE-A','fullAddress':'南京市测试街道某小区','contactName':'SECRET','phone':'SECRET'}
        b={'addressId':'PRIVATE-B','fullAddress':'南京市另一个街道小区'}
        c=Mock();c.call.return_value={'addresses':[a,b]}
        choices=address_choices(c);ref=choices['addresses'][0]['reference']
        self.assertNotIn('PRIVATE',json.dumps(choices));self.assertNotIn('SECRET',json.dumps(choices))
        c.call.side_effect=[{'addresses':[b,a]},[]]
        delivery_stores(c,ref)
        self.assertEqual(c.call.call_args.args[1]['addressId'],'PRIVATE-A')
        a['fullAddress']='地址已变化';c.call.side_effect=[{'addresses':[a,b]}]
        with self.assertRaises(ValueError):delivery_stores(c,ref)

if __name__=='__main__':unittest.main()
