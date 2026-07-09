# Mirage 幻影 · 小红书爬虫反检测加固

<sub>**Mirage** —— 让风控看见的，只是一个像真人的幻象。</sub>

> 给 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 一键打入**五层反检测加固**，
> 让小红书（XHS）自动化抓取尽量**不被风控识别** —— 不被警告、不被限流、不被封号。

**它不是又一个爬虫。** 它是一套加固工具 + 安全方法论：你已经装好的 MediaCrawler，跑一条命令，就从"机器人裸奔"变成"尽量像真人"。所有改动**自动备份、幂等、可一键还原**，绝不损坏你的文件。

**两大能力**：① 给爬虫做**五层抓取加固**（下方）；② 一套**拟人互动引擎**做安全的点赞/关注/收藏/评论（见下文「互动引擎」）。

> [!IMPORTANT]
> **用途边界**：Mirage 仅用于**学习、研究与个人合规测试**。请只用**小号**、控制频率、遵守目标平台条款与 robots 规则。
> 工具默认就帮你守住三条红线：① 互动引擎 `dry_run` 默认开，绝不替你自动实跑；② 遇验证码立即停手，**不破解人机验证**；③ 不碰主号、不做商业刷量 / 刷粉。
> 完整边界见 [使用政策与伦理边界](docs/usage-policy.md)。

## 🧭 按你的目的找路

| 你想做的事 | 去哪 |
|-----------|------|
| 怕被封，给爬虫加固 | 下方「快速开始」：`apply_hardening.py --dry-run` → 真打 → `--check` |
| 被警告 / 限流了怎么救 | [docs/safe-usage.md](docs/safe-usage.md)：立刻停手 → 切 safe 档 → 换小号 |
| 安全养号 / 点赞关注收藏 | 下方「互动引擎」（dry-run 默认，绝不替你实跑） |
| 扩到抖音 / B站 等别的平台 | 一条 `-p all` 通吃 7 平台 → [docs/platforms.md](docs/platforms.md) |
| 抖音签名挡住了（a_bogus/msToken/ttwid） | [docs/signature-layer.md](docs/signature-layer.md)：四重门 → 桥接 F2 + [桥接模板](examples/douyin_signature_bridge.py) |
| 想抓 App（不是网页版） | [docs/app-capture.md](docs/app-capture.md)：抓包 vs UI自动化 两条路 + 维护现实 |
| 证明加固真有效（出数据） | `python scripts/fingerprint_benchmark.py`：加固前后 BotScore 量化对比 |
| 弄懂原理（五层怎么防） | [docs/anti-detection.md](docs/anti-detection.md) |

```bash
python scripts/apply_hardening.py /path/to/MediaCrawler --dry-run   # 先看会改什么
python scripts/apply_hardening.py /path/to/MediaCrawler             # 真打（自动备份）
python scripts/apply_hardening.py /path/to/MediaCrawler --check     # 体检五层状态
```

## ✨ 五层防护

| 层 | 防住的风控信号 | 怎么做 |
|----|--------------|--------|
| **L1** stealth.min.js 注入 | `navigator.webdriver` 等自动化指纹 | CDP 启动浏览器时自动注入 |
| **L2** 随机抖动睡眠 | 固定间隔 = 机器节拍 | `base × U(0.7,1.6)`，6s → 实际 4.2~9.6s 随机 |
| **L3** 批次限制 + 安全参数 | 单次高曝光、无头浏览器 | 单次 ≤8 条、真 Chrome、单并发、禁无头 |
| **L4** 启动预热 | 打开即搜 = 非人类 | 首次搜索前停留 3~8s |
| **L5** 鼠标 + 滚动模拟 | 睡眠期页面"冻死" | 翻页间隔随机滚动 + 移动鼠标 |

> 原理逐层拆解见 [docs/anti-detection.md](docs/anti-detection.md)。

> 🌐 **不只小红书**：五层加固通用于 MediaCrawler 全部 **7 个平台**（小红书 / 抖音 / 快手 / B站 / 微博 / 贴吧 / 知乎），一条 `-p all` 全加固。各平台反爬强度分级与建议参数见 [docs/platforms.md](docs/platforms.md)。

## 📦 前置依赖

- **Python 3.11+**（与 MediaCrawler 一致）
- 已装好并能跑通 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)
- Playwright + Chromium（仅 `verify_stealth.py` 自检需要）：`pip install playwright && playwright install chromium`
- **核心脚本 `apply_hardening.py` 零额外依赖** —— 只用 Python 标准库，clone 下来直接能跑

## 🚀 快速开始

前提：你已经装好并能跑通 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)。

```bash
git clone https://github.com/millennialdreamer/mirage.git
cd mirage

# 1. 先 dry-run，看清楚将要改哪些文件（不落盘）
python scripts/apply_hardening.py ~/path/to/MediaCrawler --dry-run

# 2. 确认无误后真打（每个被改文件先备份成 *.xhs-stealth.bak）
python scripts/apply_hardening.py ~/path/to/MediaCrawler

# 3. 体检：确认五层都到位
python scripts/apply_hardening.py ~/path/to/MediaCrawler --check

# 反悔随时还原
python scripts/apply_hardening.py ~/path/to/MediaCrawler --revert
```

## 🧰 脚本一览

| 脚本 | 作用 |
|------|------|
| `scripts/apply_hardening.py` | ⭐核心：一键打入五层加固，幂等 / 自动备份 / 可回滚 / dry-run / 体检 |
| `scripts/safe_profile.py` | 安全档 / 常规档 / 激进档 一键切换，并预估抓取速率 |
| `scripts/verify_stealth.py` | 指纹自检：开浏览器对比"注入前/后"，确认 webdriver 等特征被隐藏 |
| `scripts/fingerprint_benchmark.py` | ⭐指纹 benchmark：加固前后 **BotScore(0~100) 量化对比** + 风险等级 + JSON 证据报告（"可证明的拟人"；真跑请自己手动） |
| `scripts/human_behavior.py` | 人类行为模拟模块（抖动睡眠 / 预热 / 鼠标滚动），可手动集成复用 |
| `scripts/weekly_maintenance.sh` | 每周更新 stealth.min.js + 检查上游有无反检测补丁 |
| `scripts/human_interaction.py` | ⭐互动引擎：识别 + 拟人点击 点赞/关注/收藏/评论（dry-run 默认） |
| `scripts/interaction_policy.py` | 互动配额：保守每日上限 + 最小间隔 + 跨 session 计数持久化 |
| `scripts/mirage_loop.py` | ⭐终极"拟人刷号"主循环：大量浏览 + 少量克制互动 + 风控熔断 |

## 🤝 互动引擎（点赞 / 关注 / 收藏 / 评论）

除了抓取加固，Mirage 还提供一套**拟人互动引擎**——像真人一样安全地点赞/关注/收藏/评论。**0 封控靠的是克制 + 拟人，不是狂刷**：

- **dry-run 默认开**：默认只把鼠标移动到位、演示不真点，确认无误才 `dry_run=False`。
- **保守每日上限 + 最小间隔 + 跨 session 计数**：杜绝秒赞、超量、重启绕过。
- **贝塞尔点击 + 先看够才赞 + 二段决策**：看了也只约 45% 才互动，把配额留给优质内容。
- **终极"拟人刷号"循环**：大量浏览 + 少量克制互动 + 遇风控（验证码/限流）自动熔断。

```python
from mirage_loop import MirageLoop
loop = MirageLoop(page, dry_run=True, conservative=True)   # 新号建议 conservative
await loop.run()
```

⚠️ 互动有**真实对外后果**（真给人点赞/评论），**只用小号**。完整安全手册见 [docs/interaction-safety.md](docs/interaction-safety.md)。

## 🛡️ 安全使用（务必先读）

加固降低概率，**不等于安全许可**。三条铁律：

1. **只用小号测试，主号永远不碰爬虫。**
2. **放量循序渐进**：首日 ≤30 条，次日 ≤100 条，中间隔几小时，绝不连续猛抓。
3. 默认走 **safe 档**；`fast` 档显著提高被风控概率，只在"豁出去快抓一把"时才用。

完整手册（含被警告后怎么办）见 [docs/safe-usage.md](docs/safe-usage.md)。

## 🔬 为什么有效

小红书风控核心判断"你像不像真人"。本工具不去破解签名，而是从**行为层**让自动化尽量贴近真人：真实 Chrome、随机节奏、人类停顿、鼠标活动。行为层比签名层更稳 —— 签名算法每隔几周会变，但"慢一点、有抖动、鼠标会动"永远像人。详见 [docs/anti-detection.md](docs/anti-detection.md)。

## ⚠️ 免责声明

仅供学习与研究。**加固只能降低被检测概率，无法消除** —— 任何爬虫都有被风控的可能。使用者须遵守小红书的使用条款与 robots 规则，合理控制频率，不得用于商业或任何不当用途。因使用本工具产生的一切后果由使用者自负。

## ⚠️ 已知边界 / 不支持

Mirage 是针对 MediaCrawler **网页版爬虫**的行为层加固工具，以下场景**超出其能力范围**，请勿误用：

1. **App 抓取（客户端）**：Mirage 只加固 Playwright 驱动的**网页版**。手机 App、桌面客户端要抓取数据，需要抓包（Charles/mitmproxy）、Hook（Frida）、模拟器等完全不同的技术栈，Mirage 对此无能为力。

2. **海外平台**：TikTok、Instagram、X（Twitter）、YouTube 等海外平台使用的是**不同爬虫框架**，不在 MediaCrawler 支持范围内，Mirage 自然也不覆盖。

3. **签名算法逆向**：抖音 `a_bogus`、小红书 `x-s`、快手签名等由 MediaCrawler 上游维护。平台一旦更新签名算法，抓取可能**暂时失效**，需等待上游跟进修复。Mirage 不参与签名逆向，`weekly_maintenance.sh` 会提示你关注上游更新。

4. **极端网络环境**：弱网、断线重连、代理不稳等场景需要配合专用的 `network_resilience` 模块处理重试与恢复。Mirage 核心模块假设网络基本畅通，不内置断线容灾。

> 简单说：Mirage 做好一件事——**让 MediaCrawler 的网页端自动化行为更像真人**。超出这个范围的需求，请寻找对应专项工具。

## 📄 License

本项目以学习研究为目的发布，继承上游 MediaCrawler 的非商用精神。详见 [LICENSE](LICENSE)。
