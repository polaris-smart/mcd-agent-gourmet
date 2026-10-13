"""Explicit, read-only member views. Never export account IDs or coupon codes."""
from .mcp import MCPError


def fields(value, names):
    if not isinstance(value, dict):
        raise MCPError('会员接口结构变化，停止展示。')
    # Only scalar allowlisted values; unknown is not zero.
    return {name: value.get(name) if type(value.get(name)) in (str, int, float, bool) else None
            for name in names}


def member_overview(client):
    account = fields(client.call('query-my-account', {}),
                     ('availablePoint', 'currentMouthExpirePoint', 'nextMouthExpirePoint', 'frozenPoint'))
    coupons, total, complete = [], None, False
    for page in range(1, 6):
        result = client.call('query-my-coupons', {'page':str(page), 'pageSize':'200'})
        if not isinstance(result, dict) or not isinstance(result.get('coupons'), list):
            raise MCPError('无法识别券包分页，不把不完整结果当作全部优惠券。')
        coupons.extend(fields(c, ('title','subtitle','enable','datetimeText','tradeStartDate','tradeEndDate'))
                       for c in result['coupons'])
        total, pages = result.get('totalCount'), result.get('totalPages')
        if type(total) is not int or total < 0 or type(pages) is not int or pages < 0:
            raise MCPError('券包分页信息缺失。')
        if result.get('currentPage') != page:
            raise MCPError('券包页码不一致，停止以免重复统计。')
        if page >= pages:
            complete = len(coupons) == total
            break
    available = client.call('available-coupons', {})
    if not isinstance(available, list):
        raise MCPError('无法识别待领取券列表。')
    return {'mode':'live_member_read_only', 'points':account,
            'owned_coupons':coupons, 'owned_total':total, 'owned_complete':complete,
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
