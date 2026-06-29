# Changelog

> 版本约定：发布前为 `0.x.y`（语义化）——x 升一位 = 一组成熟能力 / 里程碑，y = 修补。

## v0.5 — 成熟化 / 可信发布（loop 自驱多圈打磨）

经多方独立评审（按 GitHub 10k★ 标准）+ 写判分离迭代，成熟度从 6/10 → ~8/10（三方复评：工程 8 / 难反制 8.5 / 产品 7.5）。

**Added**
- 合规护栏：README 首屏用途边界三红线 + `docs/usage-policy.md` 伦理边界（防 GitHub 删库）
- `fingerprint_benchmark.py`：加固前后 BotScore 量化对比 + 风险等级 + JSON 证据报告（"可证明的拟人"，带诚实免责）
- 打包：`pyproject.toml`（package-dir 映射 scripts 成 mirage 包，可 `pip install`）+ 统一 `mirage` CLI（apply/doctor/verify/benchmark）
- `tests/test_real_anchors.py`：真实 MediaCrawler 7 平台原始 core.py 锚点回归（真 pytest）
- `scripts/ci.sh`：本地 CI（pytest + ruff + mypy + 自检），代替 GitHub Actions
- `docs/tls-fingerprint.md`：TLS/JA3 诚实边界分析（CDP 真 Chrome 页面层天然真实）
- README 顶部「按你的目的找路」用户动线导航

**Changed / Fixed**
- 核心可靠性：`write()` 升级原子写（tempfile+fsync+os.replace）；新增 `write_py_safe` 统一落盘口（原子写 + 写后 AST 校验 + 失败回滚），三处补丁全接入
- 运行时层三语境 import（扁平 / 部署 tools / pip 包）
- ruff/mypy 清理 21 个 lint/类型问题

---

## v0.4 — 多平台支持

**Added**
- `apply_hardening.py` 新增 `--platform all` 参数，一次打通全部 7 个平台
- 支持平台：小红书(xhs) / 抖音(dy) / 快手(ks) / B站(bili) / 微博(wb) / 贴吧(tieba) / 知乎(zhihu)
- 新增 `weekly_maintenance.py`（跨平台 Python 版，替代仅限 Mac/Linux 的 `.sh`）

**Changed**
- 加固逻辑通用化：锚点检测从小红书特有 API 改为平台无关的通用模式

**Notes**
- 不同平台反爬强度差异大（抖音"极高"、贴吧"低"），建议分批测试，高强度平台增大 `CRAWLER_MAX_SLEEP_SEC`

---

## v0.3 — 拟人互动引擎

**Added**
- `human_interaction.py`：点赞 / 关注 / 收藏 / 评论，**默认 `dry_run=True`**，不真点安全阀
- `interaction_policy.py`：每日配额上限 + 最小冷却间隔 + 跨 session JSON 持久化 + 跨天自动归零
- `mirage_loop.py`：拟人主循环，配额耗尽自动收工

**Notes**
- 互动功能有真实对外后果（给陌生人点赞/关注），**只用小号**，主号永不碰

---

## v0.2 — 品牌升级

**Changed**
- 项目从 `xhs-stealth-crawler` 更名为 **Mirage（幻影）**，暗指"穿越检测迷雾不留痕"
- README 重写，突出"仅供学习研究"定位

---

## v0.1 — 初始版本（小红书五层加固）

**Added**
- L1 `stealth.min.js` 自动注入 —— 隐藏 `navigator.webdriver` 等自动化指纹
- L2 随机抖动睡眠 —— 消除固定节拍这一机器特征
- L3 安全参数批量覆写 `base_config.py`（单并发 / 禁无头 / 保留登录态）
- L4 启动预热 —— 进搜索前先停留几秒，像真人看页面
- L5 贝塞尔鼠标 + 滚动模拟（`human_behavior.py`）
- `apply_hardening.py`：一键打补丁，幂等（打两次零变化）+ 自动备份 + `--revert` 完整还原
