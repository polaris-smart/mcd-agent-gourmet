# MCP_INTEGRATION

## 麦当劳 MCP Server 接入说明

### 服务器信息
- 端点：`https://mcp.mcd.cn`
- 协议：Streamable HTTP（JSON-RPC 2.0）
- 认证：Bearer Token（open.mcd.cn 手机登录后控制台申请）
- 限流：600 次/分钟/Token

### 使用的 MCP 工具

| 工具名 | 用途 | 调用场景 |
|---|---|---|
| `query-nearby-stores` | 查询附近门店 | 建立门店上下文 |
| `query-meals` | 查询门店菜单 | 营养师/预算师/口味师获取餐品列表 |
| `query-meal-detail` | 查询餐品详情 | 口味师分析套餐组成 |
| `list-nutrition-foods` | 查询营养信息 | 营养师分析营养构成 |
| `query-store-coupons` | 查询门店可用券 | 预算师计算最优方案 |
| `calculate-price` | 商品价格计算 | 预算师真实计价（不猜测） |
| `create-order` | 创建订单 | owner 审批后安全下单 |
| `query-order` | 查询订单详情 | 下单后确认状态 |

### 调用流程

```
1. 建立门店上下文
   query-nearby-stores → 用户选择门店

2. 三 agent 并行工作
   营养师：query-meals → list-nutrition-foods → 分析营养构成
   预算师：query-meals → query-store-coupons → calculate-price
   口味师：query-meals → query-meal-detail → 推荐搭配

3. 协调器汇总
   collect_proposals → 生成对比表 → owner 审批

4. 安全下单（owner 审批后）
   create-order → 返回支付链接 → owner 完成支付 → query-order 确认
```

### 业务价值

- **多 agent 协作**：不同角色 agent 分工，避免单一视角的局限
- **治理层**：两本账（需求账+预算账）+ owner 审批链，确保决策透明
- **真实计价**：所有金额来自 MCP `calculate-price`，不猜测不编造
- **fixture demo**：零 Token 零联网即可体验多 agent 协作流程
