# Changelog

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
