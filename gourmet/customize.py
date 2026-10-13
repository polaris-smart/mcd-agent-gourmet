"""Resolve explicit requests against current official special-order options."""
from .mcp import MCPError

ICE_NAMES = {'standard':'标准','less':'少冰','none':'去冰','extra':'多冰'}


def modifications(choice, ice='any', omit=()):
    groups = choice.get('modification', {}).get('items', [])
    if not isinstance(groups, list):
        raise MCPError('特调结构变化。')
    requested = set(omit)
    if ice != 'any' and ice not in ICE_NAMES:
        raise ValueError('未知冰量。')
    matched_ice = ice == 'any'
    matched_omit = set()
    values, labels = [], []
    for group in groups:
        options = group.get('values', [])
        ice_options = [o for o in options if o.get('name') in ICE_NAMES.values()]
        target = ICE_NAMES.get(ice)
        affected = bool(target and ice_options) or any(o.get('name') in requested for o in options)
        if not affected:
            continue
        if target and ice_options and sum(o.get('name') == target for o in options) != 1:
            raise MCPError('这款饮料没有唯一匹配的冰量选项。')
        selected_count = 0
        for option in options:
            quantity = option.get('selectedQuantity', 0)
            if target and ice_options:
                quantity = int(option.get('name') == target)
                matched_ice = True
            if option.get('name') in requested:
                quantity = 0
                matched_omit.add(option['name'])
                if not option.get('unselectedKey'):
                    raise MCPError('该配料没有官方去除参数，不能只写备注代替特调。')
                labels.append('去除'+option['name'])
            if type(quantity) is not int or not option.get('code'):
                raise MCPError('特调数量或编码缺失。')
            if quantity > 0:
                minimum, maximum = option.get('minQuantity', 0), option.get('maxQuantity')
                if type(maximum) is not int or quantity < minimum or (maximum >= 0 and quantity > maximum):
                    raise MCPError('特调数量不符合官方限制。')
                selected_count += 1
            key = option.get('selectedKey') if quantity else option.get('unselectedKey')
            if quantity and not key:
                raise MCPError('特调缺少 selectedKey。')
            if key:
                values.append({'code':option['code'], 'key':key, 'quantity':quantity})
        if not group.get('minValues', 0) <= selected_count <= group.get('maxValues', len(options)):
            raise MCPError('特调选择数不符合官方限制。')
        if target and ice_options:
            labels.append(target)
    if not matched_ice:
        raise MCPError('这款饮料未提供所选冰量，不会把偏好假装成已满足。')
    if matched_omit != requested:
        raise MCPError('没有找到指定配料，请先查看当前餐品的特调选项。')
    return ({'values':values} if values else None), labels
