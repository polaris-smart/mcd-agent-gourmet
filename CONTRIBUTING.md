# Contributing

欢迎提 Issue 和 PR。这个项目有两条硬规矩：**金额必须能核**、**数据缺就说未知**。

## 提 Issue

麻烦写清三件事，否则很难复现：

1. **你输入了什么**（完整命令，或网页上的条件组合）
2. **你期望什么**
3. **实际出现什么**（报错原文 / 截图）

> 不要附 Token、账号信息或原始优惠券数据。Token 只放在本机环境变量 `MCD_MCP_TOKEN` 里，永远不会进入仓库或对话。

## 提 PR

提交前本地跑一遍（和 CI 相同的四步）：

```bash
python3 -B -m unittest discover -s tests -v     # 178 项 Python 回归
node tests/parity.cjs                            # Python/JS 决策一致性（24,192 组）
python3 -B demo.py --budget 35 --taste spicy     # CLI 冒烟
python3 -B scripts/build_demo.py && git diff --exit-code -- docs/data.js
```

几个容易踩的点：

- **改了 `fixtures/` 或产出结构** → 必须重跑 `scripts/build_demo.py` 并提交 `docs/data.js`，否则 CI 的 `git diff --exit-code` 会失败。
- **改了比较/筛选逻辑** → Python 和 `docs/review.js` 要同步改，`parity.cjs` 会逐字比对两边输出。
- **改了网页样式** → `docs/style.css` 的版本号（`index.html` 里的 `?v=`）要一起改，否则回访用户会看到旧样式。
- **不要写死门店或商品编码**：核价必须来自当次 `calculate-price` 返回的整数分。

## 发布流程

版本号在 `gourmet/__init__.py`；更新 `CHANGELOG.md` 后打 tag 并构建分发包：

```bash
python3 scripts/build_skill_package.py --output /tmp/mcd-agent-gourmet.zip
```

`main` 分支受保护：合并前必须通过 `verify` 检查，禁止强推与删除。
