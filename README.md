# 麦门省钱王 · mcd-agent-gourmet

> 多 agent 协作帮你点最省的麦当劳
> 营养师+预算师+口味师分工，owner 审批后安全下单

[![Polaris-Smart LAB](https://img.shields.io/badge/Polaris--Smart-LAB-blue?style=flat-square)](https://polaris-smart.github.io)
[![GitHub](https://img.shields.io/badge/GitHub-polaris--smart-black?style=flat-square&logo=github)](https://github.com/polaris-smart)
[![X](https://img.shields.io/badge/X-%40polaris__smart-black?style=flat-square&logo=x)](https://x.com/polaris_smart)

## 用户收益

| 痛点 | 我们帮你解决 |
|---|---|
| **"怎么点最省？"** | 预算师枚举最优组合，暴露凑单陷阱 |
| **"券快过期了！"** | 主动提醒沉默成本（即将过期的券=白扔的钱） |
| **"怎么吃健康？"** | 营养师分析营养构成，标记超标项 |
| **"选择困难症"** | 三 agent 分工推荐，owner 一键审批 |

## 定位

市面上的麦当劳 Skill 都在回答"怎么点最省/怎么点最健康"。
我们回答一个更完整的问题：**"一群 agent 怎么协作帮你点餐"**。

正如麦当劳官方所说：**"帮助 AI Agent 连接麦当劳服务"**、
**"集成点餐、领券等核心能力，快速构建拥有麦当劳能力的专属 AI Agent"**——
我们在此基础上，加入**多 agent 协作**与**治理层**：
不是"一个 agent 帮你点餐"，而是"一群 agent 协作，owner 审批后安全下单"。

## 官方三大核心能力覆盖

| 官方能力 | 我们的实现 |
|---|---|
| **智能点餐** | 多 agent 协作点餐（营养师+预算师+口味师+owner 审批） |
| **日历活动抢先知** | 预算师主动提醒"券快过期"（沉默成本） |
| **优惠券周周领** | 预算师枚举最优组合（暴露凑单陷阱） |

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
