# 麦门多 agent 协作点餐 · mcd-agent-gourmet

> 基于麦当劳中国 MCP 的多智能体协作点餐 Skill
> 不同角色 agent 分工协作，owner 审批后安全下单

## 定位

市面上的麦当劳 Skill 都在回答"怎么点最省/怎么点最健康"。
我们回答一个不同的问题：**"一群 agent 怎么协作帮你点餐"**。

## 核心设计

### 角色分工（多 agent 协作）

| Agent | 角色 | 职责 |
|---|---|---|
| **营养师** | 健康守门员 | 分析营养构成，标记超标项 |
| **预算师** | 省钱专家 | 计算最优组合，暴露凑单陷阱 |
| **口味师** | 美食顾问 | 推荐搭配，考虑个人偏好 |
| **owner（你）** | 最终决策者 | 审批方案，确认下单 |

### 治理层（两本账）

- **需求账**：你想吃什么（口味/营养/份量）
- **预算账**：你愿意花多少钱（预算/券/积分）
- **审批链**：三 agent 出方案 → owner 审批 → 安全下单

### 与冠军仓的差异

| | mcd-coupon-strategist | mcd-agent-gourmet（我们） |
|---|---|---|
| 视角 | 单 agent 省钱 | **多 agent 协作** |
| 决策 | 算法排序 | **角色分工+owner 审批** |
| 输出 | 最优方案 | **多方案对比+推荐理由** |
| 治理 | 无 | **两本账+审批链** |

## 快速体验（30 秒）

```bash
git clone https://github.com/polaris-smart/mcd-agent-gourmet.git
cd mcd-agent-gourmet
python demo.py
```

**零依赖 · 零 Token · 零联网** —— fixture demo 模式

## 参赛

2026 麦当劳程序员创意开发大赛（M-CODE）
