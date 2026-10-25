## 改了什么

## 为什么

## 提交前自检

- [ ] `python3 -B -m unittest discover -s tests` 通过
- [ ] `node tests/parity.cjs` 通过（改了比较逻辑时必须两边同步）
- [ ] 改了 `fixtures/` 或产出结构 → 已重跑 `scripts/build_demo.py` 并提交 `docs/data.js`
- [ ] 改了网页样式 → 已更新 `index.html` 里的 `style.css?v=` 版本号
- [ ] 没有写死门店/商品编码；金额来自 `calculate-price` 整数分
- [ ] 没有包含 Token、账号信息或券数据
