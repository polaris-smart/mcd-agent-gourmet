"""Business context must be consistent across menu, coupons and pricing."""

CHANNELS = {'pickup': (1, 1), 'drive': (5, 1), 'delivery': (2, 2)}

# 这两类不是"个人点餐的一个渠道"，而是独立场景，数据面与流程都不同：
#   group 企业团餐 query-meal-assistance（企业专用服务与优惠逻辑）
#   party 主题派对 party-city/store/date/session + party-order-create
# 明确拒绝把它们混进个人点餐链路，避免用个人参数去套企业/活动规则。
SEPARATE_SCENARIOS = {
    'group': '企业团餐（query-meal-assistance）',
    'party': '主题派对（party-* 场次）',
}


def order_context(plan):
    fulfillment = plan.get('fulfillment', {'channel':'pickup'})
    channel = fulfillment.get('channel', 'pickup')
    if channel in SEPARATE_SCENARIOS:
        raise ValueError('%s 属于独立场景，本工具不把它与个人点餐混在一起；请使用对应的独立流程。' % SEPARATE_SCENARIOS[channel])
    if channel not in CHANNELS:
        raise ValueError('当前程序支持到店、得来速和麦乐送；企业团餐与派对须使用独立流程。')
    be_type, order_type = CHANNELS[channel]
    code = plan.get('store', {}).get('code')
    if not isinstance(code, str) or not code.isdigit():
        raise ValueError('门店编码必须是数字字符串。')
    base = {'storeCode':code, 'beType':be_type, 'orderType':order_type}
    business = fulfillment.get('be_code')
    if channel != 'pickup':
        if not isinstance(business, str) or not business:
            raise ValueError('得来速/配送必须使用同次门店查询返回的 beCode，不得沿用到店门店参数。')
        base['beCode'] = business
    elif business:
        raise ValueError('到店场景不能携带 beCode。')
    return base
