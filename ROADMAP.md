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

## 四、loop 状态
- ✅ 第一圈（诊断 + 多方评审 + roadmap）：**完成（本文件）**
- ⬜ 第二圈（执行 P0）：待启动
- ⬜ 第三圈（再评审，验收是否达 ~8/10）
