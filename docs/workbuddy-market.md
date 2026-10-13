# WorkBuddy Skill 市场发布包

可以发布。根据[官方开放平台 Skill 文档](https://open.workbuddy.cn/en/docs/skill)，市场支持安装并在对话中调用 Skill；开放平台接受 ZIP，并要求 SKILL.md 的 description、description_zh、description_en、version、author 等元数据。

## 构建与安装

```bash
python3 scripts/build_skill_package.py --output /tmp/mcd-agent-gourmet-0.3.0.zip
```

ZIP 有一个 mcd-agent-gourmet/ 根目录，包含 SKILL.md、LICENSE、references/ 和 scripts/。脚本及 gourmet/、fixtures/ 在 scripts/ 下保持相对位置。只含明确列入的公开文件；不打包 local/、私有配置、历史浏览器资料或账号响应。

安装后优先用 WorkBuddy 已配置的官方麦当劳 MCP；脚本模式需要 Python 3.9+ 和本机私有 MCD_MCP_TOKEN。默认历史演示无需 Token。Token 不随包分发。

## 上架文案

- 名称：麦门点餐议事会
- 简介：说出预算、口味、糖和冰量偏好，比较完整麦当劳餐单；按到店/外带/得来速/配送核对门店、券和费用，查询积分与兑换详情。只查询核价，由你选择。
- 示例：“35 元，不辣，无糖去冰，带走。先让我选门店，看看有什么券能用。”“积分快过期了，看看能换什么，并说明这张券是否已核验配送适用性。”
- 说明：独立参赛作品，非官方产品；网页是历史快照演示。不同入口和实测范围见 validation.md。后续修订由 Codex 辅助，历史 WorkBuddy 使用记录单列。
- 许可证：MIT（保留署名）。本包不是此前单独授权的 ClawHub MIT-0 分发包。
- 地址：https://github.com/polaris-smart/mcd-agent-gourmet

## 提交状态

包构建及离线运行验证后可提交开放平台。当前浏览器连接失败，未进入上架表单、未上传、未提交审核；不能表述为已经上架。平台账号资质、最终表单与审核要求须在实际提交时确认。
