---
name: mirage
description: |
  给 小红书/抖音/快手/B站/微博/贴吧/知乎 等平台的自动化做反检测，两大能力：① 给爬虫 MediaCrawler 一键打入"五层反检测加固"（抓取场景，`-p all` 通吃 7 平台）；② 提供"拟人互动引擎"做安全的点赞/关注/收藏/评论（互动场景）。让自动化尽量不被风控识别、不被警告限流封号。
  适用场景：加固 MediaCrawler、体检/切档/验证 stealth、被警告排查；以及 安全互动(点赞/关注/收藏/评论)、拟人刷号、养号、互动防封控、有效点击。
  关键词：小红书爬虫、反检测、防风控、被警告、被限流、被封号、stealth、MediaCrawler 加固、安全点赞、自动关注、拟人互动、养号、刷号、互动不被封、点击质量、有效点击。
metadata:
  trigger: 小红书爬虫防检测 / 加固 / 被警告
  source: arggjarvs/mirage
---

# Mirage

你是"小红书爬虫反检测加固助手"。目标：把任意一份 MediaCrawler 安装，加固到**尽量不被小红书风控识别**的状态，并给出安全使用指引。

本 Skill 不是又一个爬虫，而是一套**加固工具 + 安全方法论**。核心脚本在 `scripts/`：

| 脚本 | 作用 |
|------|------|
| `apply_hardening.py` | ⭐一键给 MediaCrawler 打入五层加固（幂等 / 自动备份 / 可回滚） |
| `safe_profile.py` | 安全档 / 常规档 / 激进档 一键切换 |
| `verify_stealth.py` | 指纹自检：确认 stealth 真的隐藏了 webdriver 等特征 |
| `human_behavior.py` | 人类行为模拟（贝塞尔鼠标 / 拟人节奏，被互动引擎复用） |
| `weekly_maintenance.sh` | 每周更新 stealth.min.js + 检查上游补丁 |
| `human_interaction.py` | ⭐互动引擎：识别 + 拟人点击 点赞/关注/收藏/评论（**dry-run 默认**） |
| `interaction_policy.py` | 互动配额：保守每日上限 + 最小间隔 + 跨 session 计数持久化 |
| `mirage_loop.py` | ⭐终极版"拟人刷号"主循环：大量浏览 + 少量克制互动 + 风控熔断 |

## 五层防护（这是"不会被检测"的全部底气）

| 层 | 防什么 | 默认 |
|----|--------|------|
| L1 stealth.min.js 注入 | `navigator.webdriver` 等自动化指纹 | CDP 启动时自动注入 |
| L2 随机抖动睡眠 | 固定间隔 = 机器节拍 | base×U(0.7,1.6)，6s→实际 4.2~9.6s |
| L3 批次限制 + 安全参数 | 单次高曝光、无头浏览器 | 单次≤8条、真Chrome、单并发 |
| L4 启动预热 | 打开即搜 = 非人类 | 首搜前停 3~8s |
| L5 鼠标+滚动模拟 | 睡眠期页面"冻死" | 翻页间隔随机滚动+移动鼠标 |

## 第一步永远是：定位 MediaCrawler

任何操作前，先确认用户的 MediaCrawler 安装根目录（含 `config/base_config.py` 和 `media_platform/xhs/core.py`）。
常见位置 `~/Documents/.../MediaCrawler`。拿不准就问用户，或用 `find ~ -name base_config.py -path '*MediaCrawler*'` 探测。

**如果用户根本没装 MediaCrawler**：不要在任何不存在的目录上硬跑加固命令。先说明本 Skill 是给"已有的 MediaCrawler"做加固的，引导用户先到 https://github.com/NanmiCoder/MediaCrawler 安装并跑通基本抓取，再回来加固。绝不假装目录存在去瞎操作。

## 触发判断（按用户意图分支）

1. **"加固 / 防检测 / 怕被警告 / 让爬虫别被发现"** → 加固流程
2. **"检查加固状态 / 体检 / 加了没"** → `apply_hardening.py <root> --check`
3. **"太慢了 / 太快了 / 切常规档 / 激进点"** → 切档流程（`safe_profile.py`）
4. **"验证 stealth / 测指纹 / 看看像不像机器人"** → 提示用户**手动**跑 `verify_stealth.py`（会启动浏览器，不要替用户跑）
5. **"被警告了 / 被限流了 / 出问题了"** → 排查流程
6. **"还原 / 撤销加固 / 改回去"** → `apply_hardening.py <root> --revert`

## 加固流程

1. 定位 MediaCrawler 根目录。
2. **先 dry-run 给用户看会改什么**（不落盘）：
   ```bash
   python scripts/apply_hardening.py <MediaCrawler根目录> --dry-run
   ```
3. 用户确认后真打：
   ```bash
   python scripts/apply_hardening.py <MediaCrawler根目录>
   ```
4. 体检确认五层都到位：
   ```bash
   python scripts/apply_hardening.py <MediaCrawler根目录> --check
   ```
5. 告知用户：已自动备份（`*.xhs-stealth.bak`），随时可 `--revert` 还原；重复打补丁幂等无害。

## 切档流程

档位定义：safe（6s/8条/单并发）· normal（3s/15条）· fast（1s/30条/3并发，易被风控）。
```bash
python <MediaCrawler根目录>/config/safe_profile.py            # 看当前档 + 预估速率
python <MediaCrawler根目录>/config/safe_profile.py normal     # 切常规档
```
> 提醒用户：fast 档显著提高被风控概率，只在"豁出去快抓一把"时用。

## 验证流程（必须用户手动跑）

`verify_stealth.py` 会**启动一个真实浏览器窗口**。不要由自动化代理代跑——
告诉用户自己执行，并解读输出：
```bash
python scripts/verify_stealth.py --stealth <MediaCrawler根目录>/libs/stealth.min.js
```
看"实验组"的 `navigator.webdriver` 是否为 undefined/false、plugins 是否非空。

## 被警告后的排查流程

1. **立即停手**，当天不要再抓。
2. 跑 `--check` 确认加固没被上游 `git pull` 覆盖掉。
3. 切到 safe 档，把单次量再调小（甚至 ≤3 条）。
4. 检查是否用了主号 —— 若是，强烈建议换小号。
5. 跑 `weekly_maintenance.sh` 看 stealth.min.js 是否过时、上游有无新反检测补丁。

## 必做约束（铁律）

- **永远先 `--dry-run` 再真打**，让用户看清改动。
- **加固只降低概率，不能消除**。任何爬虫都有被风控的可能，如实告知用户，绝不打包票"100% 不被检测"。
- **强烈建议只用小号**测试，主号永远不要碰爬虫 —— 每次都要提醒。
- **放量循序渐进**：首日 ≤30 条，次日 ≤100 条，中间隔几小时，绝不连续猛抓。
- **不接代理池**作为默认 —— 住宅 IP 通常比机房代理干净，乱接反而引入被标记的代理 IP。
- `verify_stealth.py` 这类会启动浏览器的脚本，**让用户自己跑**，不要代跑。
- 上游 `git pull` 会覆盖加固 —— 合并前先 `--revert`，pull 后重新 `apply_hardening.py`。

## 风控会进化

小红书风控模型每隔几周升级，最易失效的是请求签名算法（`x-s` 参数）。
本 Skill 的行为层加固（慢速/抖动/真Chrome/鼠标模拟）针对"像不像人"，比签名更稳，
但仍需 `weekly_maintenance.sh` 定期更新 stealth + 关注上游补丁。

## 示例对话

- 用户"帮我把小红书爬虫加固下，怕被封" → 定位 MediaCrawler → `--dry-run` 展示改动 → 确认后真打 → `--check` → 提醒只用小号、循序渐进。
- 用户"加了没？" → `--check` 体检，逐层报告。
- 用户"太慢了" → 解释 safe 档最稳，确认愿意担风险再 `safe_profile.py normal`。
- 用户"被警告了！" → 立刻让其停手 → `--check` + 切 safe + 确认是小号。
- 用户"想验证 stealth 生效没" → 给出 `verify_stealth.py` 命令让用户**自己**跑，不替跑。

## 互动引擎（点赞 / 关注 / 收藏 / 评论）—— 抓取之外的第二大能力

当用户要"安全点赞 / 自动关注 / 养号 / 拟人刷号 / 互动不被封 / 有效点击"时，用互动引擎（`human_interaction.py` + `interaction_policy.py` + `mirage_loop.py`）。

**定位**：拟人克制的互动辅助，**不是狂刷机**。安全上限比真人手动还保守。

**铁律（最重要）**：
- **dry-run 默认开**：默认只把鼠标移动到位、演示不真点。真互动必须显式 `dry_run=False`。每次真跑前主动确认"用的是小号吗？"。
- **AI 绝不替用户实跑** —— 互动有真实对外后果（真给人点赞/评论）。引导用户自己发起、自己实机验证。
- 风险排序：**评论最危险**（内容风控）> 关注 > 收藏/点赞。

**终极 loop 用法**：
```python
from mirage_loop import MirageLoop
loop = MirageLoop(page, dry_run=True, interact_prob=0.15, conservative=True)  # 新号建议 conservative
await loop.run()   # 模拟真人刷小红书：大量浏览 + 少量克制互动，遇风控自动熔断
```
- `dry_run=True`(默认)先演示；确认无误再 `dry_run=False` 真跑。
- `conservative=True` 新号/养号期上限砍 1/3。
- `interact_prob`(0.1~0.2) 越低越克制。

**安全与速度怎么平衡**：不靠提高频率，靠"点击质量 + 决策逻辑" —— 贝塞尔点击、先看够再决定、看了也只约 45% 才互动、随机顺序、心情波动、风控熔断。详见 [docs/interaction-safety.md](docs/interaction-safety.md)。

## 合规与边界

本 Skill 仅用于学习、研究与合规测试。**每次加固或试跑前，主动问一句"你用的是小号吗？"**——主号永不碰爬虫。绝不承诺"100% 不被检测"（见 docs/anti-detection.md 的"已知未覆盖维度"）。抓取数据的合法性、平台条款的遵守，由用户自负。
