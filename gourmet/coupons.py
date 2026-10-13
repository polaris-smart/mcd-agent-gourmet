"""Conservative coupon time interpretation. Never decides order eligibility."""
from collections import Counter
from datetime import datetime, time, timedelta, timezone
import re

CHINA = timezone(timedelta(hours=8), 'Asia/Shanghai')
PUBLIC_FIELDS = ('title', 'subtitle', 'enable', 'tradeStartDate', 'tradeEndDate', 'datetimeText')
DATE = r'\d{4}-\d{2}-\d{2}'
CLOCK = r'\d{2}:\d{2}'
RANGE = re.compile(rf'^({DATE} {CLOCK})\s*[-—至~～]\s*({DATE} {CLOCK})(.*)$')


def reference_time(value=None):
    if value is None:
        return datetime.now(CHINA)
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        raise ValueError('参考时间须为 ISO 日期时间。')
    return value.replace(tzinfo=CHINA) if value.tzinfo is None else value.astimezone(CHINA)


def stamp(value):
    return value.isoformat(timespec='seconds') if value else None


def boundary(value, upper=False):
    """Return a bound plus date precision. Bare end dates are exclusive next day."""
    if not isinstance(value, str):
        return None, False
    try:
        if re.fullmatch(DATE, value):
            result = reference_time(value)
            return result + (timedelta(days=1) if upper else timedelta()), True
        if re.fullmatch(rf'{DATE}[ T]{CLOCK}(?::\d{{2}})?(?:Z|[+-]\d{{2}}:\d{{2}})?', value):
            return reference_time(value.replace('Z', '+00:00')), False
    except (ValueError, OverflowError):
        pass
    return None, False


def schedule(text):
    """Recognize only complete supported grammar; unknown qualifiers stay unknown.

    Display-only datetimeText is retained separately. Local windows are derived,
    never an official eligibility verdict. Minute endpoints include that minute.
    Weekday restrictions apply to the starting day of an overnight window.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    rest = text.strip()
    lower = upper = None
    match = RANGE.fullmatch(rest)
    if match:
        try:
            lower = reference_time(match[1])
            upper = reference_time(match[2]) + timedelta(minutes=1)
        except (ValueError, OverflowError):
            return None
        if upper <= lower:
            return None
        rest = match[3].strip()
        if not rest:
            return lower, upper, None, None
    weekdays = set(range(7))
    if rest.startswith('每天'):
        rest = rest[2:].strip()
    elif rest.startswith('周'):
        m = re.match(r'周([一二三四五六日天](?:(?:[、,，](?:周)?|至周|到周|-周)[一二三四五六日天])*)\s+', rest)
        if not m:
            return None
        expression = m[1].replace('天', '日')
        numbers = ['一二三四五六日'.index(c) for c in expression if c in '一二三四五六日']
        if any(c in expression for c in ('至', '到', '-')):
            if len(numbers) != 2 or numbers[1] < numbers[0]:
                return None
            weekdays = set(range(numbers[0], numbers[1] + 1))
        else:
            weekdays = set(numbers)
        rest = rest[m.end():].strip()
    windows = []
    while rest:
        m = re.match(rf'({CLOCK})\s*[-—至~～]\s*({CLOCK})', rest)
        if not m:
            return None
        try:
            start, end = (time.fromisoformat(m[i]) for i in (1, 2))
        except ValueError:
            return None
        windows.append((start, end))
        rest = rest[m.end():]
        if rest and not re.match(r'^[\s、,，;；]+', rest):
            return None
        rest = rest.lstrip(' 、,，;；\t\n')
    if not windows:
        return None
    return lower, upper, weekdays, windows


def intervals(day, lower, upper, weekdays, windows):
    result = []
    if day.weekday() not in weekdays:
        return result
    for first, last in windows:
        start = datetime.combine(day, first, CHINA)
        end = datetime.combine(day, last, CHINA) + timedelta(minutes=1)
        if last < first:
            end += timedelta(days=1)
        start, end = max(start, lower), min(end, upper)
        if start < end:
            result.append((start, end))
    return result


def analyze_coupon(raw, now):
    if not isinstance(raw, dict):
        raise ValueError('券记录结构无法识别。')
    item = {key: raw.get(key) if type(raw.get(key)) in (str, int, float, bool) else None
            for key in PUBLIC_FIELDS}
    # Scalar validation also prevents nested private data leaking via display fields.
    item['official_status'] = ('available' if type(item['enable']) is int and item['enable'] == 1 else
                               'unavailable' if type(item['enable']) is int and item['enable'] == 0 else 'unknown')
    item.update(time_state='unknown', urgency='unknown', last_window_ends_before=None,
                next_window=None, hours_to_deadline=None, interpretation='unknown',
                store_status='not_checked')
    lower, _ = boundary(item['tradeStartDate'])
    upper, date_only = boundary(item['tradeEndDate'], upper=True)
    parsed = schedule(item['datetimeText'])
    if parsed:
        first, last, weekdays, windows = parsed
        lower = max(x for x in (lower, first) if x is not None) if lower or first else None
        upper = min(x for x in (upper, last) if x is not None) if upper or last else None
        date_only = date_only and last is None
    # Never replace an unrecognized, nonempty structured date with guessed prose.
    if any(item[k] not in (None, '') and boundary(item[k], k == 'tradeEndDate')[0] is None
           for k in ('tradeStartDate', 'tradeEndDate')):
        return item
    if lower and upper and lower >= upper:
        item['interpretation'] = 'conflicting_dates'
        return item
    deadline = None
    future = []
    if parsed and lower and upper:
        if windows is None:
            deadline = upper
            future = [(lower, upper)] if upper > now else []
        else:
            # A weekly schedule needs at most eight days, including overnight spill.
            final_day = (upper - timedelta(microseconds=1)).date()
            last_intervals = [pair for offset in range(9)
                              for pair in intervals(final_day - timedelta(days=offset), lower, upper, weekdays, windows)]
            if last_intervals:
                deadline = max(pair[1] for pair in last_intervals)
            first_day = max(now, lower).date() - timedelta(days=1)
            future = sorted(pair for offset in range(9)
                            for pair in intervals(first_day + timedelta(days=offset), lower, upper, weekdays, windows)
                            if pair[1] > now)
        item['interpretation'] = 'derived_from_display_text'
        item['time_state'] = ('within_window' if any(a <= now < b for a, b in future) else
                              'before_next_window' if future else 'no_remaining_window')
        if future:
            item['next_window'] = {'starts_at': stamp(future[0][0]), 'ends_before': stamp(future[0][1])}
    else:
        if upper and not date_only:
            deadline = upper
            item['interpretation'] = 'explicit_end_only'
        elif upper:
            item['interpretation'] = 'date_only'
        if upper and now >= upper:
            item['time_state'] = 'ended'
        elif lower and now < lower:
            item['time_state'] = 'not_started'
    if deadline:
        remaining = (deadline - now).total_seconds() / 3600
        item.update(last_window_ends_before=stamp(deadline), hours_to_deadline=round(remaining, 2))
        item['urgency'] = ('ended' if remaining <= 0 else 'within_24_hours' if remaining <= 24 else
                           'within_72_hours' if remaining <= 72 else 'within_7_days' if remaining <= 168 else 'later')
    elif item['time_state'] in ('ended', 'no_remaining_window'):
        item['urgency'] = 'ended'
    return item


def coupon_report(coupons, total, complete, now=None, mode='live_coupon_read_only'):
    current = reference_time(now)
    rows = [dict(analyze_coupon(c, current), number=i + 1) for i, c in enumerate(coupons)]
    groups = {}
    for row in rows:
        if isinstance(row['title'], str) and row['title'].strip():
            groups.setdefault(row['title'].strip(), []).append(row['number'])
    return {'mode': mode, 'generated_at': stamp(current), 'timezone': 'Asia/Shanghai',
            'total': total, 'fetched_count': len(rows), 'complete': complete, 'coupons': rows,
            'counts': dict(Counter(r['urgency'] for r in rows)),
            'attention': [r['number'] for r in sorted(rows, key=lambda r: r['hours_to_deadline'] or 0)
                          if r['urgency'] in ('within_24_hours', 'within_72_hours')],
            'same_title_groups': [v for v in groups.values() if len(v) > 1],
            'notice': '时间窗口是对官方展示文案的本地解释，非门店或订单可用承诺；分钟末点按包含该分钟解释，原文同时保留。到期不等于需要购买，同名不代表同规则或可叠加。未领券、未兑换、未下单。'}


def render_coupon_report(report):
    labels = {'within_24_hours':'24 小时内结束', 'within_72_hours':'72 小时内结束',
              'within_7_days':'7 天内结束', 'later':'较晚结束', 'ended':'时段或有效期已结束', 'unknown':'截止时刻待核验'}
    states = {'within_window':'处于已解析时间窗口', 'before_next_window':'尚未进入下一窗口',
              'no_remaining_window':'按已解析规则没有剩余窗口', 'ended':'有效期已结束',
              'not_started':'尚未开始', 'unknown':'时间窗口待核验'}
    official = {'available':'接口显示当前可用', 'unavailable':'接口显示当前不可用', 'unknown':'官方当前状态未知'}
    store = {'not_checked':'门店/渠道未核验', 'listed':'这张券列于所选门店与渠道的查询结果，仍须核价',
             'not_listed':'未列于本次门店结果，不代表券已失效', 'identity_unknown':'券身份无法可靠匹配，未按同名猜测'}
    lines = [('构造样例演示，不是你的券包' if report['mode'] == 'synthetic' else '我的券 · 本轮只读查询'),
             report['generated_at'], '已读取 %s / %s 张；%s' % (report['fetched_count'], report['total'], '分页完整' if report['complete'] else '结果不完整，不当作全部券')]
    for row in report['coupons']:
        lines += ['', '[%s] %s · %s' % (row['number'], row['title'] or '未命名券', labels[row['urgency']]),
                  '  官方原文：' + (str(row['datetimeText']) if row['datetimeText'] is not None else '未提供'),
                  '  核销日期：%s 至 %s' % (row['tradeStartDate'] or '未知', row['tradeEndDate'] or '未知'),
                  '  %s；%s' % (states[row['time_state']], official[row['official_status']]),
                  '  ' + store[row['store_status']]]
        if row['next_window']:
            lines.append('  本地解析窗口：%s 至 %s 前' % (row['next_window']['starts_at'], row['next_window']['ends_before']))
        if row['hours_to_deadline'] is not None and row['hours_to_deadline'] > 0:
            lines.append('  距最后截止约 %.2f 小时（不等于还可连续使用这么久）' % row['hours_to_deadline'])
    if report['same_title_groups']:
        lines.append('\n同名券分组（独立保留日期与条件，不推断叠加）：' + str(report['same_title_groups']))
    lines += ['', report['notice'], '需要用券时，先确认你本来想买的餐品、门店和取餐方式，再查门店券并官方核价。']
    return '\n'.join(lines)
