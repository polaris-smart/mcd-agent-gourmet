# WorkBuddy Skill 市场发布包

可以发布。根据[官方开放平台 Skill 文档](https://open.workbuddy.cn/en/docs/skill)，市场支持安装并在对话中调用 Skill；开放平台接受 ZIP，并要求 SKILL.md 的 description、description_zh、description_en、version、author 等元数据。

## 构建与安装

```bash
python3 scripts/build_skill_package.py --output /tmp/mcd-agent-gourmet-0.3.2.zip
```

ZIP 有一个 mcd-agent-gourmet/ 根目录，包含 SKILL.md、LICENSE、references/ 和 scripts/。脚本及 gourmet/、fixtures/ 在 scripts/ 下保持相对位置。只含明确列入的公开文件；不打包 local/、私有配置、历史浏览器资料或账号响应。

安装后优先用 WorkBuddy 已配置的官方麦当劳 MCP；脚本模式需要 Python 3.9+ 和本机私有 MCD_MCP_TOKEN。默认历史餐单演示与 `--coupon-demo` 构造券包演示均无需 Token。Token 不随包分发。

## 上架文案

- 名称：麦门点餐议事会
- 简介：说出预算、口味、糖和冰量偏好，比较完整麦当劳餐单；查看自己的券何时能用，分清临期、时间窗口和门店/渠道核验，再按需核价。支持积分与兑换详情查询。只查询核价，由你选择。
- 示例：“35 元，不辣，有糖可乐去冰，带走。先让我选门店，看看有什么券能用。”也支持“无糖可乐去冰”，按用户选择处理，不默认无糖。“积分快过期了，看看能换什么，并说明这张券是否已核验配送适用性。”
- 说明：独立参赛作品，非官方产品；网页是历史快照演示。不同入口和实测范围见 validation.md。后续修订由 Codex 辅助，历史 WorkBuddy 使用记录单列。
- 许可证：MIT（保留署名）。本包不是此前单独授权的 ClawHub MIT-0 分发包。
- 地址：https://github.com/polaris-smart/mcd-agent-gourmet

## 提交状态

v0.3.2 已导入本机 WorkBuddy，“已安装技能”显示启用，并完成一轮客户端离线构造券演示。客户端的本地导入不是市场投稿；已安装技能详情菜单仅提供编辑、打开文件夹和卸载。根据[开放平台概述](https://open.workbuddy.cn/docs)，市场发布需在开放平台完成入驻/资质、资产创建、审核和上线。用户确认目前尚未完成开放平台个人开发者认证；[官方入驻指南](https://open.workbuddy.cn/docs/onboarding)要求本人身份资料及人脸核验，应由本人在平台完成。当前未进入上架表单、未上传市场、未提交审核；不能表述为已经上架。认证完成后使用本节的 ZIP、文案和地址填写实际表单，并以平台回执为准。
