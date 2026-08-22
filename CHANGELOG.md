# Changelog

> 版本约定：发布前为 `0.x.y`（语义化）——x 升一位 = 一组成熟能力 / 里程碑，y = 修补。

## v0.6 — 观测位与一致性（多方审 + 红队读源码后的深度补齐）

**Added**
- `soft_ban_radar.py` + `mirage radar`：⭐**软封杀早期预警**。验证码率↑ / 返回完整度↓ / 延迟漂移 / 蜜罐命中 / 成功率下降斜率 五前兆看趋势，在**被封之前**判断"正在被降权"。跨 session 基线、多账号隔离、样本 <12 明确返回"数据不足"不瞎猜
- `device_profile.py` + `mirage profile`：⭐**统一设备画像 + 自洽校验**（一致性 > 单值伪装）+ **种子化确定性** canvas/audio 噪声（同 profile 跨会话恒定 —— 每次随机在 2026 已反成判伪证据）
- `fingerprint_benchmark.py --botd` / `--detect-url`：接第三方真实分源（FingerprintJS BotD 判定 / 真检测页通过率 + 全页截图）
- patchright 优先加载：补掉注入脚本**原理上补不了**的 CDP `Runtime.Enable` / `Console.enable` 驱动层泄漏
- `MirageLoop(on_captcha=...)`：验证码回调钩子。**Mirage 不破解验证码**，只做"检测 → 挂钩 → 回填时机拟人化"

**Fixed**
- 贝塞尔轨迹**匀速** → smoothstep 缓入缓出（实测加速比 1.14 ≈ 匀速 → 3.4 真人式加减速）。原 docstring 声称"匀加速→匀减速"但代码未实现
- 点赞/收藏校验**恒为 True**：默认查 `aria-pressed`，小红书按钮无此属性 → 没点上也报"已生效"还扣配额。改多属性快照 + 三态诚实判定
- 时间分布 `uniform` → 对数正态（实测偏度 -0.01 平顶矩形 → +1.43 右偏）。注入的 L2/L4 模板同步改，L5 兜底的直线匀速也改缓入缓出
- benchmark 措辞诚实化：删除"可证明的拟人 / 证据报告"等夸大表述（本地 7 信号是自打的相对分，**不是证据**）
- 测试不再硬编码个人路径（改环境变量 `MIRAGE_TEST_MEDIACRAWLER` + 自动探测）

**Docs**
- `anti-detection.md` 纠错：此前写"Runtime.Enable 属驱动层改造、超出定位"是**判断错误**（patchright 让它成为一行依赖替换）；补充 stealth.min.js 已被上游 deprecated 且其随机 canvas 噪声原理已反成指纹信号
- 明确注入层**架构性天花板**：TLS/JA3、worker realm 对拍、toString 审计、执行时序竞态四道原理绕不过 —— 对静态检测有效（约 7-8 成），对 CreepJS 主动对拍封顶约 4-5 成

---

## v0.5 — 成熟化 / 可信发布（loop 自驱多圈打磨）

经多方独立评审（按 GitHub 10k★ 标准）+ 写判分离迭代，成熟度从 6/10 → ~8/10（三方复评：工程 8 / 难反制 8.5 / 产品 7.5）。

**Added**
- 合规护栏：README 首屏用途边界三红线 + `docs/usage-policy.md` 伦理边界（防 GitHub 删库）
- `fingerprint_benchmark.py`：加固前后 BotScore 量化对比 + 风险等级 + JSON 证据报告（"可证明的拟人"，带诚实免责）
- 打包：`pyproject.toml`（package-dir 映射 scripts 成 mirage 包，可 `pip install`）+ 统一 `mirage` CLI（apply/doctor/verify/benchmark）
- `tests/test_real_anchors.py`：真实 MediaCrawler 7 平台原始 core.py 锚点回归（真 pytest）
- `scripts/ci.sh`：本地 CI（pytest + ruff + mypy + 自检），代替 GitHub Actions
- `docs/tls-fingerprint.md`：TLS/JA3 诚实边界分析（CDP 真 Chrome 页面层天然真实）
- `docs/signature-layer.md` + `examples/douyin_signature_bridge.py`：抖音签名四重门（a_bogus/msToken/ttwid/webid）→ 桥接 F2（Apache-2.0）实证模板 + 诚实维护现实
- `docs/app-capture.md`：App 抓取 2026 真实栈地图（抓包 frida 绕 pinning vs Appium UI 自动化；关键坑"抓包≠搞定、照样撞签名"；Mirage 边界外只给地图）
- `docs/overseas.md`：海外平台 2026 两层地图（公开 yt-dlp / 账号态 X·IG·TikTok 全栽 pacing）+ 三深坑收敛方法论（curl_cffi 补 TLS + pacing 同源）
- `docs/platform-coverage.md`：全平台覆盖矩阵**穷尽版**（海内外主流全盘：内容/电商/本地生活/音乐/长视频/资讯/招聘/微信/地图 + 海外 视频/社交/论坛/IM/图集/地图评价/职业；2026 最新活维护栈 + 新鲜度诚实标注 + Scrapling/curl_cffi 通用武器）
- `examples/bridges_quickref.py`：活维护 clean-API 栈最小正确桥接模板（yt-dlp/PRAW/Telethon/instagrapi，偏旧 crack 库不写虚模板）
- `mirage canary`：离线失效体检（加固标记/安全参数/stealth/锚点失配，退出码语义，不开浏览器）
- `mirage guard-install` / `guard-uninstall`：给 MediaCrawler 装 git post-merge hook，pull 后提示加固是否被上游覆盖（提示模式、不静默改源码）
- 核心类型注解（`interaction_policy.Policy` 数据模型）+ `.github/` issue/PR 模板 + `docs/signature-layer.md`·`app-capture.md`·`overseas.md` 三深坑地图
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
