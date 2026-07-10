## 改动说明

<!-- 改了什么、为什么 -->

## 自检清单
- [ ] `bash scripts/ci.sh` 全绿（pytest + ruff + mypy + benchmark 自检）
- [ ] 没动功能标记 `[xhs-stealth]` / 备份后缀 `.xhs-stealth.bak`（改了会让已部署环境的 `--check`/`--revert` 失灵）
- [ ] 涉及改写第三方源码的，走了 `write_py_safe`（原子写 + AST 校验 + 失败回滚）
- [ ] 若加了会启动浏览器的脚本，保持"让用户手动跑、AI/CLI 不代跑"的铁律
- [ ] 边界诚实：不承诺"100% 不被检测"（见 `docs/`）

> 合规：仅供学习研究；不加入破验证码 / 主号刷量等能力。
