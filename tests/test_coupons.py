"""Business boundary tests with synthetic coupons; no account or network access."""
import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import demo
from gourmet.coupons import analyze_coupon, coupon_report, reference_time, render_coupon_report
from gourmet.member import my_coupons
from gourmet.mcp import MCPError


def coupon(**changes):
    return dict({'title':'构造早餐券', 'enable':0, 'tradeStartDate':'2026-10-14',
                 'tradeEndDate':'2026-10-15', 'datetimeText':'05:00-10:29'}, **changes)


def analyze(now, **changes):
    return analyze_coupon(coupon(**changes), reference_time(now))


def page(rows, current=1, total=None, pages=1):
    return {'coupons':rows, 'totalCount':len(rows) if total is None else total,
            'currentPage':current, 'totalPages':pages}


class CouponTimes(unittest.TestCase):
    def test_tomorrow_uses_rolling_label(self):
        r = analyze('2026-10-14 20:00')
        self.assertEqual(r['urgency'], 'within_24_hours')
        self.assertIn('2026-10-15', r['last_window_ends_before'])

    def test_before_breakfast_is_not_currently_in_window(self):
        r = analyze('2026-10-14 01:15', tradeEndDate='2026-10-14')
        self.assertEqual(r['time_state'], 'before_next_window')
        self.assertEqual(r['hours_to_deadline'], 9.25)
        self.assertIn('05:00', r['next_window']['starts_at'])

    def test_inside_window_does_not_override_official_unavailable(self):
        r = analyze('2026-10-14 09:00')
        self.assertEqual(r['time_state'], 'within_window')
        self.assertEqual(r['official_status'], 'unavailable')
        self.assertEqual(r['store_status'], 'not_checked')

    def test_closing_minute_and_next_minute(self):
        self.assertEqual(analyze('2026-10-15 10:29:59')['time_state'], 'within_window')
        self.assertEqual(analyze('2026-10-15 10:30')['urgency'], 'ended')

    def test_date_only_end_keeps_final_evening_window(self):
        conditions = dict(tradeEndDate='2026-10-16',
                          datetimeText='周一至周五 10:30-23:59')
        for clock in ('19:00', '23:59:59'):
            with self.subTest(clock=clock):
                r = analyze('2026-10-16 '+clock, **conditions)
                self.assertEqual(r['time_state'], 'within_window')
                self.assertEqual(r['urgency'], 'within_24_hours')
                self.assertGreaterEqual(r['hours_to_deadline'], 0)
                if clock == '19:00':
                    self.assertEqual(r['hours_to_deadline'], 5.0)
                self.assertEqual(r['last_window_ends_before'],
                                 '2026-10-17T00:00:00+08:00')
        self.assertEqual(analyze('2026-10-17 00:00', **conditions)['urgency'], 'ended')

    def test_expired_deadline_does_not_move(self):
        a, b = (analyze('2026-10-15 '+t) for t in ('11:00','12:00'))
        self.assertEqual(a['last_window_ends_before'], b['last_window_ends_before'])
        self.assertEqual(a['last_window_ends_before'], '2026-10-15T10:30:00+08:00')

    def test_missed_today_can_use_tomorrow(self):
        r = analyze('2026-10-14 11:00')
        self.assertEqual(r['time_state'], 'before_next_window')
        self.assertEqual(r['next_window']['starts_at'], '2026-10-15T05:00:00+08:00')

    def test_explicit_end_not_extended_by_daily_window(self):
        r = analyze('2026-10-15 13:00', tradeEndDate='2026-10-15 12:00:00', datetimeText='10:30-23:59')
        self.assertEqual(r['last_window_ends_before'], '2026-10-15T12:00:00+08:00')
        self.assertEqual(r['urgency'], 'ended')

    def test_explicit_midnight_not_date_only(self):
        r = analyze('2026-10-15 13:00', tradeEndDate='2026-10-15 00:00:00', datetimeText='')
        self.assertEqual(r['last_window_ends_before'], '2026-10-15T00:00:00+08:00')
        self.assertEqual(r['urgency'], 'ended')

    def test_date_only_without_clock_stays_imprecise(self):
        r = analyze('2026-10-15 09:00', datetimeText='')
        self.assertIsNone(r['last_window_ends_before'])
        self.assertEqual(r['urgency'], 'unknown')
        self.assertEqual(analyze('2026-10-16', datetimeText='')['urgency'], 'ended')

    def test_full_timestamp_range_without_repeated_short_clock(self):
        r = analyze('2026-10-15 11:00', datetimeText='2026-10-15 05:00-2026-10-15 10:29')
        self.assertEqual(r['last_window_ends_before'], '2026-10-15T10:30:00+08:00')
        self.assertEqual(r['urgency'], 'ended')

    def test_weekday_restriction_last_window_can_precede_expiry_date(self):
        r = analyze('2026-10-17 11:00', tradeEndDate='2026-10-18', datetimeText='周一、二、三、四、五 10:30-23:59')
        self.assertEqual(r['last_window_ends_before'], '2026-10-17T00:00:00+08:00')
        self.assertEqual(r['urgency'], 'ended')

    def test_weekend_waits_until_monday_when_validity_allows(self):
        r = analyze('2026-10-17 11:00', tradeEndDate='2026-10-21', datetimeText='周一至周五 10:30-23:59')
        self.assertEqual(r['next_window']['starts_at'], '2026-10-19T10:30:00+08:00')

    def test_multiple_windows_keep_gap(self):
        r = analyze('2026-10-14 09:00', datetimeText='05:00-08:00、10:00-12:00')
        self.assertEqual(r['time_state'], 'before_next_window')
        self.assertIn('10:00', r['next_window']['starts_at'])

    def test_overnight_window_uses_starting_weekday(self):
        r = analyze('2026-10-15 01:00', datetimeText='周三 22:00-02:00')
        self.assertEqual(r['time_state'], 'within_window')
        self.assertEqual(r['next_window']['starts_at'], '2026-10-14T22:00:00+08:00')

    def test_unknown_qualifiers_or_invalid_clock_do_not_become_full_day(self):
        for text in ('节假日除外 05:00-10:29', '25:99-26:99', '周一到五 05:00-10:29', '05:00-10:29 限指定活动'):
            with self.subTest(text=text):
                r = analyze('2026-10-14 09:00', datetimeText=text)
                self.assertEqual(r['time_state'], 'unknown')
                self.assertIsNone(r['last_window_ends_before'])

    def test_conflicting_dates_stay_unknown(self):
        r = analyze('2026-10-14', tradeStartDate='2026-10-20')
        self.assertEqual(r['interpretation'], 'conflicting_dates')
        self.assertEqual(r['urgency'], 'unknown')

    def test_bad_structured_end_not_ignored(self):
        r = analyze('2026-10-14', tradeEndDate='待定', datetimeText='2026-10-15 05:00-2026-10-15 10:29')
        self.assertEqual(r['urgency'], 'unknown')

    def test_timezone_is_business_timezone(self):
        utc = datetime(2026,10,14,1,tzinfo=timezone.utc)
        self.assertEqual(reference_time(utc).hour, 9)
        self.assertEqual(analyze_coupon(coupon(), reference_time(utc))['time_state'], 'within_window')


class CouponReports(unittest.TestCase):
    def test_all_rows_kept_and_ended_not_actionable(self):
        rows = [coupon(tradeEndDate='2026-11-01'), coupon(title='已结束样例', tradeEndDate='2026-10-14')]
        r = coupon_report(rows, 2, True, '2026-10-15 11:00')
        self.assertEqual(len(r['coupons']), 2)
        self.assertEqual(r['attention'], [])
        self.assertEqual(sum(r['counts'].values()), 2)

    def test_same_name_is_only_grouping_not_deduplication(self):
        r = coupon_report([coupon(), coupon(tradeEndDate='2026-10-19', datetimeText='10:00-12:00')], 2, True, '2026-10-14')
        self.assertEqual(r['same_title_groups'], [[1,2]])
        self.assertNotEqual(r['coupons'][0]['datetimeText'], r['coupons'][1]['datetimeText'])
        self.assertNotIn('可能可叠加', render_coupon_report(r))

    def test_redaction_includes_nested_unexpected_display_fields(self):
        r = coupon_report([coupon(id='SECRET', code='SECRET', accountId='SECRET',
                                  datetimeText={'code':'SECRET'}, subtitle=['SECRET'])], 1, True, '2026-10-14')
        self.assertNotIn('SECRET', json.dumps(r))
        self.assertIsNone(r['coupons'][0]['datetimeText'])

    def test_synthetic_demo_is_labelled_and_offline(self):
        for args in (['--coupon-demo'], ['--coupon-demo','--json']):
            output = io.StringIO()
            with patch('demo.Client') as client, redirect_stdout(output):
                self.assertEqual(demo.main(args), 0)
            client.assert_not_called()
            self.assertTrue('构造样例' in output.getvalue() or 'synthetic' in output.getvalue())

    def test_privacy_actions_cannot_save_or_mix(self):
        for args in (['--my-coupons','--save-snapshot','no.json'], ['--coupon-demo','--my-coupons'],
                     ['--my-coupons','--live'], ['--my-coupons','--channel','delivery'],
                     ['--coupon-demo','--store-code','123']):
            with patch('demo.Client') as client, redirect_stderr(io.StringIO()):
                self.assertEqual(demo.main(args), 2)
            client.assert_not_called()

    def test_my_coupons_only_reads_wallet_and_fetches_pages(self):
        c = Mock()
        c.call.side_effect = [page([coupon(id='a',code='x')], total=2,pages=2),
                              page([coupon(id='b',code='y')],current=2,total=2,pages=2)]
        r = my_coupons(c, now='2026-10-14')
        self.assertTrue(r['complete'])
        self.assertEqual(len(r['coupons']), 2)
        self.assertEqual([x.args for x in c.call.call_args_list], [
            ('query-my-coupons', {'page':'1','pageSize':'200'}),
            ('query-my-coupons', {'page':'2','pageSize':'200'})])

    def test_changed_pagination_stops(self):
        c = Mock(); c.call.side_effect = [page([coupon()],total=2,pages=2), page([],2,total=3,pages=2)]
        with self.assertRaises(MCPError): my_coupons(c)

    def test_store_match_requires_identity_pair_not_name(self):
        c = Mock(); c.call.side_effect = [page([coupon(id='id-1',code='code-1'), coupon(id='id-2',code='code-2'), coupon()]),
            [{'title':'同名不作匹配','couponId':'id-1','couponCode':'code-1'}]]
        plan = {'store':{'code':'123'}, 'fulfillment':{'channel':'delivery','be_code':'paired'}}
        r = my_coupons(c, plan, '2026-10-14')
        self.assertEqual([x['store_status'] for x in r['coupons']], ['listed','not_listed','identity_unknown'])
        self.assertNotIn('code-1', json.dumps(r)); self.assertNotIn('id-1', json.dumps(r))
        self.assertEqual(c.call.call_args.args, ('query-store-coupons', {'storeCode':'123','beType':2,'orderType':2,'beCode':'paired'}))

    def test_invalid_store_context_stops_before_wallet_access(self):
        c = Mock()
        with self.assertRaises(ValueError):
            my_coupons(c, {'store':{'code':'123'}, 'fulfillment':{'channel':'delivery'}})
        c.call.assert_not_called()

    def test_cli_context_and_text_output(self):
        c = Mock(); c.call.side_effect = [page([coupon()]), []]
        with patch('demo.Client', return_value=c), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(demo.main(['--my-coupons','--store-code','123']), 0)
        self.assertIn('我的券', output.getvalue())
        self.assertEqual(c.call.call_args.args[1], {'storeCode':'123','beType':1,'orderType':1})


if __name__ == '__main__':
    unittest.main()
