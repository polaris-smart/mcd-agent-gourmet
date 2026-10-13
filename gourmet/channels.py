"""Business context must be consistent across menu, coupons and pricing."""

CHANNELS = {'pickup': (1, 1), 'drive': (5, 1), 'delivery': (2, 2)}


def order_context(plan):
    fulfillment = plan.get('fulfillment', {'channel':'pickup'})
    channel = fulfillment.get('channel', 'pickup')
    if channel not in CHANNELS:
        raise ValueError('当前程序支持到店、得来速和麦乐送；企业团餐须使用独立流程。')
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
