# Mirage 改进路线图（10k 星标准 · loop 第一圈产出）

> 来源：8-agent 工作流（3 路天花板调研 + 4 维 10k 评审 + 综合），主线（Claude）终审裁决。
> 当前评级：**约 6/10 成熟度**。补齐下方 P0 后可达 ~8/10。
> ⚠️ 工作流中 3 个 agent（签名/文档/实用性评审）因 socket 掉线，结论已由其余 agent 覆盖。

## 一、天花板突破——诚实结论（不再嘴硬说"物理不可能"，也不吹"全突破"）

### App 抓取：🟡 难但可做（**不是**物理天花板）
- **路线A 抓包 + 绕 SSL pinning**（mitmproxy + frida/objection）：能抓明文，但真坑是**签名复刻**。小红书有现成开源签名库（`Spider_XHS` / `xhshow` / `xhscrawl`）可跳过造签名；抖音（a_bogus + ollvm 混淆 + VMP）**难一个量级**。
- **路线B Appium / Airtest UI 自动化**：绕开所有签名，慢但稳，适合少量精准采集。
- **路线C 云手机群控 + RPA + 代理 IP 池**：规模化矩阵（单号月 ~10 元）。
- **务实建议**：小红书优先（现成轮子最成熟）；抖音走 UI 自动化，**别硬刚签名**（猫鼠游戏，单兵不划算）。

### 海外平台：🟡 难但可做，但 Mirage 正确姿势 = **指路牌 + 借方法论**，不是"做加固器"
- 对口库：YT→`yt-dlp`、IG→`instaloader`、X→`twscrape`/`twikit`、TikTok→`TikTok-Api`。
- Mirage 的 **L1/L5（浏览器指纹）只对"驱动真浏览器"的库有意义**；**L2/L3/L4（保守配额 + 抖动 + 预热 + 熔断）可抽象成平台无关的 pacing 中间件**，对怕封号的真账号库（twscrape/instaloader）对症。
- **认知坑（最大代差）**：2026 海外平台普遍上了 IP 信誉 / TLS 指纹 / 服务端行为分析，**stealth 已是失效区**，不能把中文平台"行为层比签名稳"的经验外推。

### 签名：🟡 靠现成库 + 监控，不从零逆向
- 小红书/抖音/B站签名有部分开源库可集成；自己逆向新签名（尤其抖音）维护成本极高。
- **务实**：集成现成签名库 + 签名失效自动告警 + 靠上游 MediaCrawler。

## 二、补齐 10k 差距（架构评审 6/10 揪出的真 gaps —— 实打实该做）

### P0 — 从"单人脚本"迈向"可信仓库"最关键
- [ ] `pyproject.toml`（可 `pip install`）+ 各包 `__init__.py`，**干掉 `sys.path.insert` + 双 import hack**
- [ ] 测试改**真 pytest**（assert/fixture/参数化/coverage），替换手搓 print 计数器
- [ ] **给真正风险面写测试**：拿一棵 **pin 版本的真实 MediaCrawler 目录**端到端验证 `apply_hardening` 的正则锚点命中 / 改写后 AST 可 parse / `--check`/`--revert` 闭环 / 上游结构变更优雅降级
- [ ] **本地 CI 脚本**（prepublish 风格，代替 GitHub Actions —— 额度禁 Actions）：一键 pytest + ruff + mypy

### P1
- [ ] 全量类型注解 + ruff/mypy 配置
- [ ] 改名 `XhsInteractor`→`Interactor`（已多平台），README 标题去"小红书"专属
- [ ] `DANGER_PHRASES` / locale 判断从硬编中文改成**可配置**（多语言/可扩展）
- [ ] dy/bili 选择器加"健康检查"机制 + 与已验证的 xhs 明确区分可信度

## 三、诚实标注边界（写进 README，不装全能）
- 签名从零逆向 → 靠现成库/上游
- 海外平台服务端行为分析 → stealth 失效区，需住宅代理 + 账号轮换（另一笔预算）
- App 群控规模化 → 工作室级投入

## 五、完善方向 v2（loop 第二圈 · 三方独立评审综合）

> 来源：DeepSeek(工程) / MiMo(战略难反制) / Kimi(产品存活) **各自独立产出**（互不可见）+ Claude 终审。
> ⭐三方强共识（多模型独立指向同一处）= 最高信号；按"生存→跃迁→广度"重排优先级。

### 档一 · 生存线（P0，不做就别上 GitHub）
1. **合规护栏防删库**（Kimi P0 + 双重死亡预警）—— 首屏加粗"仅学习研究/禁生产账号/禁商业刷量"；代码 dry_run 默认强制、显式才关；`usage-policy.md` 伦理边界；海外敏感平台措辞克制。**这是生存问题，不是锦上添花。**
2. **核心可靠性：原子写 + 改后 AST 校验**（DeepSeek P0）—— 改写第三方源码必须 `tempfile`→`os.replace` 原子替换；改完先 `ast.parse` 验证语法有效才落盘，失败完整回滚。崩溃损坏用户源码 = 致命。
3. **测真风险面 + 多版本回归**（DeepSeek 深化 v1-P0③）—— 拿 pin 版**真实 MediaCrawler**（含多历史版本）对正则锚点做快照/回归测试，证明对上游漂移鲁棒。**排在打包之前**（见下方顺序修正）。

### 档二 · 跃迁线（P0–P1，差异化与信任）
4. **可证明的拟人：指纹 benchmark**（MiMo P0）—— 对接 CreepJS / FingerprintJS / BrowserScan，跑加固前后对比，输出 BotScore(0–100) + 各维度(webdriver/canvas/timing/mouse)偏差热力图。**从"我说有效"到"数据证明有效"——Mirage 凭什么 10k star 的最强差异化。**
5. **统一 `mirage` CLI 入口**（DeepSeek+Kimi P0）—— typer/click，子命令 `apply/revert/check/run/doctor`，废除一堆 `python scripts/xxx.py`。从"脚本集合"到"工具"。
6. **打包 pyproject + PyPI**（v1-P0① + Kimi）—— 干掉 sys.path hack，可 `pip install`。**排在测试核心之后**。
7. **用户动线 README + 文档工程**（DeepSeek 批判 + Kimi P0）—— 从"五层 L1–L5 + 脚本清单"改成场景动线（我怕被封 / 我被警告了 / 我想养号 / 我想扩平台）；5 分钟 quickstart + 架构图。

### 档三 · 抗衰减与广度（P1–P2，务实）
8. **失效自动监测告警**（MiMo P1）—— canary 探针定期验证加固是否仍生效，失效自动告警。抗衰减核心，让加固不会"悄悄失效"。
9. **海外 pacing 中间件**（MiMo P1，广度 ROI 最高先落）—— 抽象 L2/L3/L4 成平台无关中间件，配 yt-dlp/twscrape/instaloader + 平台行为模板。
10. **结构化日志 + 配置系统**（DeepSeek P1）—— structlog 替 print；`mirage.yaml` 集中配置 + 环境变量覆盖。
11. **TLS/JA3 + IP 信誉维度**（MiMo P2）—— curl-impersonate 对齐 JA3 指纹；启动前过滤高风险 IP。头部平台已用此层联合判定。
12. **诚实声明不覆盖维度**（MiMo+Kimi）—— README 明列**不处理**：canvas/webgl 像素差、字体枚举、账号行为图谱、设备传感器、长期会话一致性；引导配合代理 + 养号。

### 明确不做（三方共识 · 防无底洞）
- ❌ 从零逆向抖音 a_bogus/VMP（生命周期常<7天，2026 业界"多数已死"）→ **桥接 F2（Apache-2.0，已解决四重门 a_bogus/msToken/ttwid/webid）** + curl_cffi 补 JA3 + `mirage canary` 监测失效（见 docs/signature-layer.md + examples/douyin_signature_bridge.py）。
- ❌ App 抓取框架内置（架构膨胀+合规风险）→ 已写 **docs/app-capture.md**（两条路：抓包 frida 绕 pinning + 回 F2 补签名 / Appium UI 自动化绕签名；2026 活维护栈实证 + 军备赛现实）。
- ⚠️ 上游死耦合不可能全解 → git hook(pull 前 --revert / pull 后重打) 缓解 + 长线推上游 plugin 接口。

### 对 v1 ROADMAP 的修正（接受 DeepSeek 批判）
- **顺序**：测核心锚点(真 MediaCrawler) → 原子写安全 → 打包 → CLI → 文档（**不是先打包**）。
- **"全量类型注解"降级**：聚焦公共 API / 配置 / 核心数据模型，内部渐进，不强求全量。

## 六、loop 状态
- ✅ 第一圈（诊断 + 多方评审 + v1 路线）
- ✅ 第二圈（完善方向头脑风暴 + 三方独立评审 + v2 综合）
- ✅ 第三圈（执行档一·生存线 P0）：**完成**
  - ✅ 合规护栏（README 首屏用途边界 + docs/usage-policy.md）
  - ✅ 原子写 + AST 校验（`write_py_safe` 统一落盘口；国产 QA 审 9 条，终审采纳 2 条、挡掉 7 条；自测 9 项全绿）
  - ✅ 测真锚点（tests/test_real_anchors.py；真实 7 平台 core.py 回归全绿，pytest 2 passed；"通吃 7 平台"经真代码验证属实）
- ✅ 第四圈（档二·跃迁线）：**完成**
  - ✅ 指纹 benchmark（`fingerprint_benchmark.py`：BotScore 量化 + 风险等级 + JSON 证据报告；国产审采纳 3/5；self-test 过）
  - ✅ 用户动线导航（README 顶部「按你的目的找路」6 入口导航表，不推翻结构、不丢细节）
  - ✅ 打包 pyproject + `mirage` CLI（`package-dir` 映射 scripts **不重命名**→保 skill 结构；`mirage apply/doctor/verify/benchmark`；运行时层三语境 import；国产审采纳 2 条、挡 2 条会砸 skill 的伪建议）
- ✅ 第五圈（再评审验收）：三方独立复评 **工程 8 / 难反制 8.5 / 产品 7.5 ≈ 8/10**（原 6 → +2）。三方均判"敢放 GitHub / 敢用 / 能活"= 达**可信发布门槛**，但**未到 9**。
- 🔄 第六圈（档三·冲 9）进行中：
  - ✅ 本地 CI（`scripts/ci.sh`：pytest + benchmark 自检 + ruff + mypy，代替 GitHub Actions）+ pyproject 加 ruff/mypy 配置；**首跑即抓修 21 个 lint/类型真问题**（f-string/import 排序/分号/no-redef）；三语境 import 复验仍 ok
  - ✅ TLS/JA3 诚实分析（MiMo 深析 + 我裁决 ②：CDP 真 Chrome 页面层 TLS 天然真实、签名 httpx 层缺口属请求层）→ 产出 docs/tls-fingerprint.md（划界 + curl_cffi 指引，不越界接管）
  - ✅ 版本节奏（v0.5.0 统一 CHANGELOG/pyproject/__init__，修版本错位）
  - ✅ 加固失效监测（`mirage canary` 离线体检：加固标记/安全参数/stealth/锚点失配 + 退出码；多方 plan 产出，去掉"自动开浏览器"改纯离线 + 指纹层提示手动）
  - ✅ **签名层突破**（boss 端到端撞抖音四重门 → 实证 F2/Apache-2.0 真实 API 全解四门 → `examples/douyin_signature_bridge.py` 可运行桥接模板 + `docs/signature-layer.md` 诚实维护现实；把"档三只指路牌"升级成实证模板，不自己逆向）
  - ✅ **App 抓取地图**（深坑续：`docs/app-capture.md`，2026 实证 抓包(httptoolkit/frida-unpinning) vs UI自动化(Appium3) 两条路 + 关键坑"抓包≠搞定、照样撞签名回 F2" + 军备赛现实；Mirage 边界外，只给地图不接管）
  - ✅ **海外平台地图**（深坑三部曲收官：`docs/overseas.md`，2026 实证两层[公开 yt-dlp 零风险 / 账号态 X·IG·TikTok]；★洞察三坑收敛=curl_cffi 补 TLS + pacing 方法论同源；Mirage 边界外，给指路牌+方法论）
  - ✅ 解耦上游（git hook `mirage guard-install`/`guard-uninstall`：pull 后**提示模式**检测加固被覆盖、不静默改源码；多方 plan 方案 + 我裁决；六项测试 + apply 回归全过，顺带逼出并修掉 `__main__` 吞退出码的真 bug）
  - ✅ 核心类型注解（`interaction_policy.Policy` 数据模型全注解；mypy 逼出 `_counts`/`_last` 缺注解已修；非全量，DeepSeek 说全量被高估）+ `.github/` issue/PR 模板（贴合 Mirage 特性：canary/[xhs-stealth]/write_py_safe/合规）
- **第六圈档三 8 项全部完成** ✅ —— CI / TLS / 版本 / 失效监测 / 签名层 / App / 海外 / guard / 类型注解 + 模板
- ✅ 第七圈（复评验收）：三方独立复评 **工程 7.8 / 难反制 9.2 / 产品 8.7 ≈ 8.6**。难反制到顶、超预期；产品最后 0.3 = 真实用户/社区/3 个月发布验证（**真实世界时间锁，非代码**）；工程是唯一可代码补的短板。
- ✅ 第八圈（工程冲 9）：补 DeepSeek 点名的 3 硬伤 —— 结构化日志（`_logging.py` + mirage_loop 9 处 print→分级 log，CLI 保留彩色）/ CI 自动触发（`.githooks/pre-push`）/ mypy 拓宽到全 scripts（13 文件全绿）。
- ✅ 第九圈（工程复核）：DeepSeek **7.8→8.6**；它另列的 2 个"距 9 差距"（缺 pyproject / 测试不可移植）**经我核实均为幻觉**——pyproject.toml 在且可 pip install、test_real_anchors 有可移植层 + 真实环境自动 skip（71 行守卫）。修正后工程 ≈ 9。

## 七、终局判读（诚实）

**综合 ≈ 8.9**（工程 ~9 修正后 / 难反制 9.2 / 产品 8.7）。**代码层已到天花板**：
- 三方现在要么**幻觉已做完的东西**（DeepSeek 的 pyproject/测试），要么要**真实世界采用时间**（产品的真实用户/社区/3 个月发布）——**都不是靠写代码还能往上顶的**。
- 真·剩余差距 = **真实世界时间**（boss 端到端 + 真实用户跑起来 + 数月稳定发布），非代码。
- **结论：核心代码 loop 完成**（继续刷代码 = 镀金/追幻觉）。
- ⟳ **但 boss 点出"覆盖度地图"是真漏项**——我只盘了 MediaCrawler 7 + 3 深坑，没自觉盘全市场。已补 `docs/platform-coverage.md`：国内电商(淘宝 mtop/拼多多 anti_content)/本地生活(美团 mtgsig/点评字体加密)/微信生态(公众号活维护栈)/招聘(zp_token)/海外(Reddit PRAW·LinkedIn/Amazon 超边界) 2026 实证矩阵 + 各栈新鲜度诚实标注。方法论收敛不变。**二次穷尽扩全**（+音乐 musicdl / 长视频 yt-dlp·webvideo-downloader / Telegram Telethon / Reddit PRAW / Google-Yelp curl_cffi / Scrapling 自愈框架）+ `examples/bridges_quickref.py` 给活维护 clean-API 栈写真模板（py_compile + 懒加载验证过）。
- 唯一剩的对外动作 = **push GitHub（待 boss 拍板）**。

## 八、第十圈：5 路深挖多方审（2026-07，"赋能更多"专项）

**推翻了"代码到天花板"的结论**——上一轮说"再刷代码=镀金"，但这轮 5 路深挖（竞品实现 / 指纹深度 / 检测生态 / 市场痛点 / 红队读真源码）挖出**真 bug 和真缺口**，说明天花板判早了。

### 已修（实测验证 + 已提交）
- ✅ **贝塞尔匀速** → smoothstep 缓入缓出。实测加速比 **1.14（≈匀速=机器人）→ 3.4（真人式加减速）**。原 docstring 写"匀加速→匀减速"但代码没实现 = 承诺即代码违约。
- ✅ **点赞校验恒 True** → 多属性快照 + 三态诚实判定。原默认查 `aria-pressed`，小红书赞按钮没这属性 → `before=None` → 恒判"已生效"，没点上也报成功还扣配额。
- ✅ **benchmark 接第三方真实分源**：`--botd`（FingerprintJS 开源 BotD 确定性判定）+ `--detect-url` 真解析 sannysoft 通过率。证据强度分档：第三方判 > 本地自打分 > MOCK。
- ✅ **patchright 优先**：补掉注入脚本**原理上补不了**的 CDP `Runtime.Enable`/`Console.enable` 驱动层泄漏；`mirage doctor` 检测提示；纠正了文档里"属驱动层改造超出定位"的错误判断（它其实是一行依赖替换）。

### 关键情报（改变判断）
- 🔴 `stealth.min.js` **2025-02 已被上游 deprecated**，且其**随机 canvas 噪声原理已反成指纹信号**（检测方同页跑两遍比 hash，真机恒定而随机噪声不一致 → 判伪造）。L1 从"停更"降级为"部分有害"。
- 🔴 **CreepJS trust score 2026 已被官方打码禁用**，读不到——别信任何"能读 CreepJS 分数"的方案。
- 🔴 **注入脚本层的天花板是架构性的**（toString 泄漏 / 执行时序竞态 / worker realm 逃逸 / 属性描述符特征四道原理绕不过），封顶约 4-5 成，过不了 CreepJS 主动对拍。要突破必须重编译内核（camoufox 路线）——**明确不追**。

### 待做（按优先级，均在定位内）
- ✅ **P1 软封杀早期预警**（★护城河）**已落地** → `scripts/soft_ban_radar.py` + `mirage radar` + 已接进 `mirage_loop`（警戒自动降速 ×1.5~2、危险自动停）。五前兆信号：验证码触发率↑ / 返回完整度↓（降权最典型：能返回但缩水）/ 延迟中位漂移 / 蜜罐命中（确凿证据，一次即进警戒）/ 成功率下降斜率。设计要点：跨 session 基线持久化、多账号隔离、中位数抗离群、**样本 <12 明确返回"数据不足"而不是瞎猜**、零依赖纯 stdlib。探针 8 项实测（健康流不误报 / 全面恶化报危险 88 分 / 仅"静默缩水"这一最隐蔽信号也能抓到 / 蜜罐不被稀释 / 持久化 / reset / 多账号隔离）。**它是 `_danger()` 的前置**：`_danger` 是"已弹验证码"的急刹，雷达是"还没被封但正在被盯上"的预警。
- ⬜ **P1 统一设备画像 + 自洽校验**：一致性 > 单值伪装。"改了 webdriver 却没整体画像 = 局部真整体假，比不改更易被交叉核对抓"。注入层可做 7-8 成。
- ⬜ **P1 随机分布全 uniform → 对数正态/指数**：真人时间行为右偏；且注入的 L2 用裸 `random.uniform`，**没走 `human_sleep` 的长尾逻辑**，文档宣称的"对数正态"在注入层不成立。
- ⬜ **P2 种子化确定性 canvas 噪声**（同 profile 跨会话稳定，替代"每次随机"这一已失效做法）。
- ⬜ **P2 验证码回调钩子**（不自研求解，暴露事件让用户自配 CapSolver/2Captcha key）。

### 明确不做（新增红线）
自研打码求解 / 自建代理池 / 整机反检测浏览器（别变第二个 Multilogin）/ 分布式调度框架 / Canvas·WebGL 引擎级伪装（注入层原理不可达）。

### 方法论教训（第二次了）
审计 agent **两次编造致命 bug**：①MiMo 说 gallery-dl/instagrapi/musicdl "已死"（GitHub 一查全是当月发版）②红队说"stealth.min.js 下载处≠注入读取处、L1 是空的"（两处都是 `<root>/libs/`，一致）。**多方审必须配事实终审**——不核实就动手，会去修不存在的问题、还可能改坏正确代码。
