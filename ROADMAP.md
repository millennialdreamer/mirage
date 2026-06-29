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
- ❌ 从零逆向抖音 a_bogus/VMP（生命周期常<7天）→ 只集成现成签名库 + 失效告警。
- ❌ App 抓取框架内置（架构膨胀+合规风险）→ 只做《App 抓取避坑指南》+ 指路牌(Spider_XHS/Appium/云手机模板)。
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
- 🔄 第四圈（档二·跃迁线）进行中：
  - ✅ 指纹 benchmark（`fingerprint_benchmark.py`：BotScore 量化 + 风险等级 + JSON 证据报告；国产审采纳 3/5，移除易误报 permMismatch、补 languages、加免责防假精确；self-test 过）
  - ⬜ 用户动线 README 重组（按"我怕被封 / 被警告了 / 想养号 / 扩平台"组织）
  - ⬜ 打包 pyproject（`package-dir` 映射 scripts，不物理重命名 → 兼顾 skill 结构）+ `mirage` CLI
- ⬜ 第五圈（再评审，验收是否达 ~9/10）
