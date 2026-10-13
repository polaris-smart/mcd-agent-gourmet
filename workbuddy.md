# WorkBuddy 使用记录与证据状态

更新日期：2026-10-14。

## 当前实现

本项目的餐单比较使用确定性筛选、排序和非支配集合计算，比较价格、营养数据与口味偏好。它没有三个独立模型并行讨论，也没有已经验证的多 Agent 协商或 owner 审批链。用户选择餐单是选择比较结果，不会创建订单、支付或兑换。

`SKILL.md` 为 WorkBuddy 等 AI 客户端提供对话流程；Python CLI 负责可重复的查询、核价与本地计算。CLI 的测试结果不能代替 WorkBuddy 客户端端到端验证。

## 历史材料修正

本文件原先包含一份标为 2026-10-12 的开发对话整理，声称“三 agent 并行工作”“US iLab 沙盒实跑”“真实 fixture”和“审批链验证”。目前没有经过本次核验的原始对话导出、工具轨迹或录屏能支持这些断言；原文可在 Git 历史中追溯，但不再作为当前功能说明或奖励核验凭证。

此次删除未经证实的成果陈述，不将它们改写成已经发生的另一份 WorkBuddy 对话。后续修订与验证使用 Codex 辅助，不冒充 WorkBuddy 操作。

## 可以核对的现有证据

- 代码与测试：仓库 `gourmet/`、`tests/` 及 GitHub Actions。
- 官方 MCP 联调的已执行范围与未验证项：[验证记录](docs/validation.md)。
- 可安装分发包的构建方式：[WorkBuddy 市场说明](docs/workbuddy-market.md)。

## 2026-10-14 WorkBuddy 客户端实测

用户将 v0.3.2 ZIP 导入本机 WorkBuddy，并确认可用。Codex 在客户端“已安装技能”中看到 `mcd-agent-gourmet`，开关开启，详情显示 `version: 0.3.2`。随后使用“去试试”在附加该 Skill 的新对话中发送明确限定为本地构造数据的测试请求。客户端对话报告实际在 `/Users/interia/.workbuddy/skills/mcd-agent-gourmet` 下执行 `python3 scripts/demo.py --coupon-demo --json`，退出码 0、stderr 为空；输出为合法 JSON，`mode: synthetic`、总数与已读取数均为 6。此处记载的是客户端界面显示的执行回报；代码中该分支在构造 MCP Client 前返回，且读取的是随包分发的构造 fixture。

这次验证覆盖本机安装、Skill 附加和离线构造券演示。尚未在 WorkBuddy 客户端完成真实 MCP 券包、选店与用券核价的整条对话，也未取得技能市场提交或审核回执。对话中没有使用真实账户、Token 或配送地址。

## 专项奖励证据状态

本文件记录了真实 WorkBuddy 客户端的离线演示，但**不是已完成 WorkBuddy 专项奖励条件的证明**。真实 MCP 对话和市场提交若发生，应另外记录客户端版本、运行时间、版本提交号、用户输入、实际工具调用与输出，以及经过脱敏的原始记录位置。不得用 CLI 测试或说明文案替代未执行的流程；是否符合专项条件由活动主办方核验。
