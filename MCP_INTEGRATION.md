# MCP 接入与验证边界

Server：`https://mcp.mcd.cn`；协议：Streamable HTTP；认证：本机环境 `MCD_MCP_TOKEN`，作为 Bearer header。示例配置只使用环境变量占位符。官方文档：[M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server)。

## 实际调用

| 工具 | 已实现用途 |
|---|---|
| `query-nearby-stores` | CLI Client/Skill 可查询门店；本次真实联调用它确认南京东城汇餐厅 |
| `query-meals` | 实时验证所选套餐在当前门店菜单内 |
| `query-meal-detail` | 读取真实套餐轮次与可替换项，生成完整明细 |
| `list-nutrition-foods` | 解析官方表格，按名称精确匹配并加总；缺失保留 null |
| `query-store-coupons` | 查询门店券；原始账号数据不保存进公开快照；默认模板不使用券 |
| `calculate-price` | 六份候选分别核价，以返回整数分 `price` 为总价 |

上述六种工具已实际调用。程序不实现下单、支付、积分兑换、自动领券。角色审阅基于同一份结构化事实，避免各角色重复查询账号数据。

## 本次核实的接口细节

- `query-nearby-stores` 位置搜索传 `beType=1, searchType=2, city, keyword`。
- 到店即时场景使用 `storeCode, beType=1, orderType=1`，不传 beCode。
- 菜单 `currentPrice` 为展示用元字符串，**不能当作完整候选的官方最终价格**。
- 核价请求用 `items`；每项用 `productCode`、`quantity`。套餐明细用 `roundList`，其中 `round` 为字符串，子项在 `comboItemList` 中。
- 核价返回 `data.price` 是整数分。拒绝缺失、负值和不明确单位；不回退到菜单价。
- 2026-10-13 的营养响应 `data` 是 TOON 风格表格字符串，内含 `productName, energyKcal, protein, sodium` 等列；Python 用标准库 csv 解析。
- 客户端先 initialize，再 notifications/initialized、tools/list。支持 JSON 与 SSE 响应、响应 ID 验证、Mcp-Session-Id；没有 session 时重新初始化。
- JSON-RPC error、工具 isError、业务失败、HTTP 错误均停止；不把历史数据伪装成实时数据。
- 只读工具白名单在客户端强制执行；HTTP 重定向被禁止，避免凭证跨站传递。

## 用券支持

`--list-coupons` 显式查询后只展示名称与匹配候选；`--live --coupon-title 名称 --coupon-candidate 候选ID` 在内存中解析标识。默认无券实时路径不调用券服务。名称不唯一或商品不匹配时停止，不把单品券套到套餐。

高级候选可在私有计划文件中显式提供 `coupon: {couponId, couponCode}`，两字段成对，仍由官方核价决定是否可用。不自动领取、不枚举券、不计算“过期即损失”，不承诺最优优惠。

本次六份正向核价均未使用券。用券字段与错误处理有代码路径；真实可用券成功核价尚未验证，不能宣传为已验证。

## 数据流

本机环境中的凭证 → 官方 MCP；官方菜单、详情与核价 → 本机规则比较；公开网页仅包含经过白名单字段整理的历史餐单。公开快照不含账号、手机号、位置坐标、订单、券 ID 或 Token。

具体价格与命令结果见 [验证记录](docs/validation.md)。
