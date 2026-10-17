# MCP 接入与验证边界

Server：`https://mcp.mcd.cn`；协议：Streamable HTTP；认证：本机环境 `MCD_MCP_TOKEN`，作为 Bearer header。示例配置只使用环境变量占位符。官方文档：[M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server)。

## 业务价值

1. **把"菜单展示价"换成"官方当次核价"**：菜单价可能附带条件（随单购卡、限时段），核价才是实付；两者不同时同时说明条件与核价，避免误解。
2. **把"怎么点更划算"算成可复算的数字**：以同店真实核价为基线（如"单品直选"），输出「省 ¥X（Y%）」；实测示例：巨无霸+中薯条+可乐中杯 单品直选 ¥48.50 vs 三件套 ¥36.50，省 ¥12.00（24.7%）。
3. **人数作一等输入**：份数完备性（主食与饮料各 ≥ 人数）、人均价与结构标签随人数变化，覆盖一个人到两个人。
4. **只读不写**：领券、下单、兑换、地址写入、抽奖均不在白名单；不产生交易风险。
5. **失败即停**：实时查询失败就停，不拿历史快照冒充实时价；未知营养不当 0、不给健康评分。

## 实际调用

v0.3.0 新增会员积分、券包、待领券、积分餐品券目录及详情入口；前四种查询已实测成功，详情按官方 schema 实现并做契约测试。新增配送地址和门店入口已做契约测试，尚未读取私人地址做联调。完整工具地图见 [references/mcp-capabilities.md](references/mcp-capabilities.md)。

新增去冰四份组合、少冰＋去酱各自实际核价成功。特调使用当前详情的 selectedKey，并提交应有的 unselectedKey；去配料后不沿用标准营养合计。程序自动组餐仅接受已核对类别的餐品编码，不能凭三个轮次就假设是完整一餐。

菜单、券与核价使用统一履约上下文：到店 1/1 无 beCode；得来速 5/1、配送 2/2 使用各自门店返回的 beCode。堂食/外带来自官方核价取餐选项。配送和得来速的真实核价仍未验证。

| 工具 | 已实现用途 |
|---|---|
| `query-nearby-stores` | CLI Client/Skill 可查询门店；本次真实联调用它确认演示门店 |
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
