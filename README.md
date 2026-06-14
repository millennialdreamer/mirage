# Mirage 幻影 · 小红书爬虫反检测加固

<sub>**Mirage** —— 让风控看见的，只是一个像真人的幻象。</sub>

> 给 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 一键打入**五层反检测加固**，
> 让小红书（XHS）自动化抓取尽量**不被风控识别** —— 不被警告、不被限流、不被封号。

**它不是又一个爬虫。** 它是一套加固工具 + 安全方法论：你已经装好的 MediaCrawler，跑一条命令，就从"机器人裸奔"变成"尽量像真人"。所有改动**自动备份、幂等、可一键还原**，绝不损坏你的文件。

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

## 📦 前置依赖

- **Python 3.11+**（与 MediaCrawler 一致）
- 已装好并能跑通 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)
- Playwright + Chromium（仅 `verify_stealth.py` 自检需要）：`pip install playwright && playwright install chromium`
- **核心脚本 `apply_hardening.py` 零额外依赖** —— 只用 Python 标准库，clone 下来直接能跑

## 🚀 快速开始

前提：你已经装好并能跑通 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)。

```bash
git clone https://github.com/arggjarvs/mirage.git
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
| `scripts/human_behavior.py` | 人类行为模拟模块（抖动睡眠 / 预热 / 鼠标滚动），可手动集成复用 |
| `scripts/weekly_maintenance.sh` | 每周更新 stealth.min.js + 检查上游有无反检测补丁 |

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

## 📄 License

本项目以学习研究为目的发布，继承上游 MediaCrawler 的非商用精神。详见 [LICENSE](LICENSE)。
