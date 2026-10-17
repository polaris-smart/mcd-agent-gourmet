"""Location-keyword search; never reads device location or changes stores silently."""
from .mcp import MCPError
from .member import fields
import hashlib


def search_stores(client, city, keyword, channel="pickup"):
    if not city or not city.strip() or not keyword or not keyword.strip():
        raise ValueError('请输入城市和位置关键词，例如 --city 南京 --keyword 新街口。')
    if channel not in ('pickup','drive'):
        raise ValueError('配送门店必须先选择配送地址，再使用 --delivery-stores。')
    rows = client.call('query-nearby-stores', {'beType':1 if channel == 'pickup' else 5, 'searchType':2, 'city':city.strip(), 'keyword':keyword.strip()})
    if not isinstance(rows, list):
        raise MCPError('门店搜索结构变化，未沿用示例门店。')
    stores = []
    for row in rows:
        view = fields(row, ('storeCode','beCode','storeName','address','distance','businessStatus','businessStartTime','businessEndTime','reservation'))
        if not isinstance(view['storeCode'], str) or not view['storeCode'].isdigit():
            raise MCPError('门店编码缺失，请重新查询。')
        options = row.get('reservationTimeOptions', [])
        if not isinstance(options, list):
            raise MCPError('无法识别预约时间。')
        view['reservationTimeOptions'] = [fields(o, ('date','reservationOptionText','today')) for o in options]
        stores.append(view)
    return {'stores':stores, 'channel':channel, 'notice':'到店/得来速门店，按位置关键词搜索；未读取设备定位。请选择 storeCode 后再核价，未随机换店。当前程序只支持即时餐单，预约选项仅供查看。'}


def delivery_addresses(client):
    result = client.call('delivery-query-addresses', {})
    rows = result.get('addresses') if isinstance(result, dict) else None
    if not isinstance(rows, list) or not all(isinstance(r, dict) and isinstance(r.get('addressId'), str) and r['addressId'] and isinstance(r.get('fullAddress'), str) for r in rows):
        raise MCPError('配送地址结构变化，停止展示。')
    return rows


def address_ref(row):
    return hashlib.sha256((row['addressId']+'\0'+row['fullAddress']).encode()).hexdigest()[:16]


def address_choices(client):
    rows = delivery_addresses(client)
    return {'addresses':[{'reference':address_ref(row), 'label':row['fullAddress'][:10]+'…（后续门牌已隐藏）'} for row in rows],
            'notice':'仅显示地址开头，不显示姓名、电话及后续门牌。选择可辨认的地址 reference 后查询配送门店；如无法辨认请先在官方应用核对，不能猜测。结果只显示在本次本地查询中，不保存。'}


def delivery_stores(client, reference):
    rows = delivery_addresses(client)
    matches = [row for row in rows if address_ref(row) == reference]
    if len(matches) != 1:
        raise ValueError('地址不存在、已变化或不唯一，请重新查询；不会按变动后的列表序号选地址。')
    address_id = matches[0]['addressId']
    stores = client.call('delivery-query-stores', {'addressId':address_id, 'beType':2})
    if not isinstance(stores, list):
        raise MCPError('配送门店结构变化。')
    return {'stores':[dict(fields(s, ('storeCode','beCode','storeName','businessStatus','businessStartTime','businessEndTime','reservation')), reservationTimeOptions=[fields(o, ('date','reservationOptionText','today')) for o in s.get('reservationTimeOptions', [])]) for s in stores],
            'notice':'仅针对这次选中地址查询；storeCode 与 beCode 必须成对使用。查询不下单；费用以整单核价为准。'}
