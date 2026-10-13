"""Explicit, read-only member views. Never export account IDs or coupon codes."""
from .mcp import MCPError
from .coupons import coupon_report
from .channels import order_context


def fields(value, names):
    if not isinstance(value, dict):
        raise MCPError('会员接口结构变化，停止展示。')
    # Only scalar allowlisted values; unknown is not zero.
    return {name: value.get(name) if type(value.get(name)) in (str, int, float, bool) else None
            for name in names}


def owned_coupon_pages(client):
    """Private raw records stay in memory; callers must explicitly redact."""
    coupons, total, complete = [], None, False
    expected = None
    for page in range(1, 6):
        result = client.call('query-my-coupons', {'page':str(page), 'pageSize':'200'})
        if not isinstance(result, dict) or not isinstance(result.get('coupons'), list):
            raise MCPError('无法识别券包分页，不把不完整结果当作全部优惠券。')
        total, pages = result.get('totalCount'), result.get('totalPages')
        if type(total) is not int or total < 0 or type(pages) is not int or pages < 0:
            raise MCPError('券包分页信息缺失。')
        if result.get('currentPage') != page:
            raise MCPError('券包页码不一致，停止以免重复统计。')
        if expected is not None and expected != (total, pages):
            raise MCPError('查询期间券包发生变化，请重新查询；未拼接不同版本的分页。')
        expected = (total, pages)
        if not all(isinstance(c, dict) for c in result['coupons']):
            raise MCPError('券包记录结构无法识别。')
        coupons.extend(result['coupons'])
        if len(coupons) > total:
            raise MCPError('券包记录数超过总数，停止以免重复统计。')
        if page >= pages:
            complete = len(coupons) == total
            break
    return coupons, total, complete


def my_coupons(client, plan=None, now=None):
    context = order_context(plan) if plan is not None else None
    raw, total, complete = owned_coupon_pages(client)
    report = coupon_report(raw, total, complete, now)
    if context is not None:
        listed = client.call('query-store-coupons', context)
        if not isinstance(listed, list) or not all(isinstance(c, dict) for c in listed):
            raise MCPError('无法识别门店券列表。')
        def pair(c, names):
            values = tuple(c.get(k) for k in names)
            return values if all(isinstance(v, str) and v for v in values) else None
        identities = {pair(c, ('couponId', 'couponCode')) for c in listed}
        identities.discard(None)
        for source, row in zip(raw, report['coupons']):
            identity = pair(source, ('id', 'code'))
            row['store_status'] = ('identity_unknown' if identity is None else
                                   'listed' if identity in identities else 'not_listed')
        report['store_context'] = {'store_code': context['storeCode'],
                                   'channel': plan.get('fulfillment', {}).get('channel', 'pickup')}
    return report


def member_overview(client):
    account = fields(client.call('query-my-account', {}),
                     ('availablePoint', 'currentMouthExpirePoint', 'nextMouthExpirePoint', 'frozenPoint'))
    raw, total, complete = owned_coupon_pages(client)
    coupons = [fields(c, ('title','subtitle','enable','datetimeText','tradeStartDate','tradeEndDate')) for c in raw]
    available = client.call('available-coupons', {})
    if not isinstance(available, list):
        raise MCPError('无法识别待领取券列表。')
    return {'mode':'live_member_read_only', 'points':account,
            'owned_coupons':coupons, 'owned_total':total, 'owned_complete':complete,
            'coupon_report':coupon_report(raw, total, complete),
            'claimable_coupons':[fields(c, ('couponName','couponStatus','label')) for c in available],
            'notice':'券包中的券不等于当前门店可用；请用 --list-coupons 按门店核验。积分不直接折现金；只查询，未领券、未兑换、未下单。'}


def points_products(client):
    result = client.call('mall-points-products', {'catRuleIds':'1>4'})
    if not isinstance(result, list):
        raise MCPError('无法识别积分餐品券目录。')
    return {'products':[fields(p, ('spuId','spuName','point','price','status','upTime','downTime')) for p in result],
            'notice':'仅查询餐品券目录。列表展示价不保证可兑换；选择 spuId 后用 --points-detail 查询 SKU、兑换现金及核销额外现金。积分不按固定比例折现。'}


def points_detail(client, spu_id):
    if type(spu_id) is not int or spu_id <= 0:
        raise ValueError('spuId 须从积分商品目录选择。')
    result = client.call('mall-product-detail', {'spuId':spu_id})
    if not isinstance(result, dict) or not isinstance(result.get('skuList'), list):
        raise MCPError('无法识别积分商品详情。')
    view = fields(result, ('spuId','spuName','shopId','upTime','downTime','note'))
    # Preserve official purchase notice verbatim; never parse prose into business rules.
    view['skuList']=[fields(s, ('skuId','points','price','extTradePrice')) for s in result['skuList']]
    view['channel_eligibility'] = {'pickup':'not_verified', 'takeaway':'not_verified', 'drive':'not_verified', 'delivery':'not_verified'}
    view['channel_notice'] = '积分商品目录不是渠道适用证明。购买须知原文展示；拥有兑换券后，仍须用目标门店、业务场景查询 query-store-coupons 并官方核价。到店的堂食/外带选项来自 takeWayList；不推断全部兑换券支持麦乐送。'
    view['notice']='points 为兑换积分；price 为兑换所需金额；extTradePrice 为用券时额外支付金额，保留官方原值，不相互混算。不表示已兑换或已满足门店条件；本工具不执行兑换，请在官方渠道核实金额、规则并完成。'
    return view
