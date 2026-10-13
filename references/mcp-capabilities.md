# MCP 能力与本项目边界

依据 2026-10-13 实际 `tools/list` 返回的 35 个工具及[官方接入仓库](https://github.com/M-China/mcd-mcp-server)。接口可能变化，运行时重新发现。本文是独立实现说明，不是官方规则副本。

| 用户需求 | MCP 工具 | 本版本状态 |
|---|---|---|
| 到店/得来速门店 | query-nearby-stores | CLI 已接入；到店搜索实测返回 |
| 当前菜单、套餐组成、特调 | query-meals / query-meal-detail | 已接入；真实详情确认糖类餐品、冰量和配料选项 |
| 整单与费用 | calculate-price | 已接入；到店历史核价已验证，新增特调验证见 validation |
| 餐品营养 | list-nutrition-foods | 已接入；标准份量精确名称匹配，特调去配料后不沿用原总数 |
| 我的积分、过期积分 | query-my-account | 已接入并实测；没有会员等级接口，不推断等级 |
| 我的券、待领券 | query-my-coupons / available-coupons | 已接入并实测；--my-coupons 单独分页清点，不查积分或待领券，区分时间窗口和官方当前状态 |
| 指定门店与渠道可用券 | query-store-coupons | 已接入到店/得来速/配送参数；真实用券成功仍需适配券 |
| 积分兑换目录、SKU 详情 | mall-points-products / mall-product-detail | 已接入；CLI 目录限餐品券；不自动兑换 |
| 配送地址、可配送门店 | delivery-query-addresses / delivery-query-stores | 已接入并做契约测试；未读取真实地址做联调 |
| 订单复购与进度 | order-list / query-order | 已识别，未接入 CLI；需要刷新菜单与核价，不能照抄旧价 |
| 商城兑换记录 | mall-order-list / mall-order-detail | 已识别，未接入 CLI |
| 活动与时间 | campaign-calendar / now-time-info | 已识别，未接入 CLI |
| 积分抽奖信息、奖品 | query-lottery-info / query-my-prizes | 已识别，未接入 CLI；不自动抽奖 |
| 团餐优惠、助餐服务 | query-promotions / query-meal-assistance | 已识别，仅企业团餐，不能套到普通个人订单 |
| 活动城市/店/日期/场次 | query-party-city / query-party-store / query-party-store-date / query-party-store-session | 已识别，未接入 CLI |
| 满意度关联奖券 | query-survey-coupon | 已识别，需要真实订单号，未接入 CLI |
| 领取、下单、兑换、地址写入、抽奖、取消 | auto-bind-coupons / create-order / mall-create-order / party-order-create / delivery-create-address / draw-lottery / cancel-order | 均不在程序白名单，不执行 |

## 到店、外带和送到家不能混用

- 到店：`beType=1, orderType=1`，无 `beCode`；堂食/外带属于核价返回的 `takeWayList` 选项，不能自造代码。
- 得来速：`beType=5, orderType=1`，需要得来速门店返回的成对 `beCode`。
- 麦乐送：用户选择已有地址后获取配送店，`beType=2, orderType=2`，必须携带对应 `beCode`。
- 团餐：`beType=6, orderType=2`，还有专用服务和优惠逻辑，本版本不支持。

价格结果保留 `deliveryPrice`、`packingPrice`、`tablewarePrice`，未知为 null。总应付始终来自官方 price，不再重复加上已包含的费用。

## 积分不是通用现金，积分券不是通用渠道券

`mall-product-detail` 的 `points`、`price`、`extTradePrice` 分别展示兑换积分、兑换金额、用券时额外金额，保留接口原值，不假定它们与核价的“分”采用相同单位。`note` 完整原文展示。积分数量不能直接换算成预算扣减，也不能把目录有商品等同于可兑换。

尚未兑换的券：读商品须知，渠道资格标未核验。已经拥有的券：先定门店与渠道，再用 query-store-coupons 核验可用商品，最后 calculate-price。到账/适用/价格三件事分别验证；不为测试花积分。

## 偏好能力

| 偏好 | 实现方式 | 数据不足时 |
|---|---|---|
| 无糖/含糖 | 已核对商品编码属性，选择真实饮料 | 标未知，不能满足指定硬条件 |
| 标准/少冰/去冰/多冰 | 当前商品 modification 的 selectedKey | 停止该特调，不写成已满足 |
| 去酱/去菜 | 当次配料原名，包含 unselectedKey 处理 | 不猜配料、不沿用原营养总数 |
| 中杯/大杯等 | Skill 只接受当次详情真实 choices；CLI 当前自动枚举仅两种中杯饮料 | 尚未自动扩展全部杯型 |
| 辣度等级、儿童玩具、过敏原 | 尚无完成验证的程序处理 | 不声称支持或安全 |

已核对类别餐品组成的即时三轮完整套餐是当前自动构造范围；陌生餐品编码会停止，而非仅凭轮次猜主食/小食/饮料。不可把四件套、单品、早餐、多人套餐套成三轮结构。程序应解释不支持并让用户重新选择。

## 券包时间解释与门店匹配

`--my-coupons` 使用北京时间，保留完整脱敏券明细；`--member` 中也附有同一报告。`datetimeText` 是官方展示文案，解析值标明为本地派生结果，不作为官方资格判定。支持完整日期时间范围、日常时段、星期列表/范围、多段和跨午夜；其他条件不能完整解释时保留原文，标待核验。纯日期不编造精确截止；分钟末点按包含该分钟解释，并与官方原文并列展示。

指定门店与渠道后，查询 `query-store-coupons`，仅用内存中的卡包 id/code 与门店 couponId/couponCode 成对匹配。同名不证明同券，匹配成功不等于已经核价。缺少稳定标识时标身份待核验；没有匹配不能说整张券已失效。到店结果还不能独自证明外带取餐资格。

分页最多 5 页、每页 200 条；页码不符或分页期间总数变化停止，超过范围时标结果不完整。已过期与临期分开；完整清单包含不临期券；同名分组不合并日期、不推断叠加。公开 `--coupon-demo` 只用构造样例。
