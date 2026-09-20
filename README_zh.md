<h1 align="center">Mirage · 蜃景</h1>

<p align="center">
  <strong>在被封号之前，先知道自己已经被限流了。</strong>
</p>

<p align="center">
  给 <a href="https://github.com/NanmiCoder/MediaCrawler">MediaCrawler</a> 做行为层加固，
  外加一个所有反检测工具都忘了做的预警雷达。
</p>

<p align="center">
  <a href="https://github.com/millennialdreamer/mirage/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/millennialdreamer/mirage/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-blue">
  <img alt="Dependencies" src="https://img.shields.io/badge/core%20deps-zero-brightgreen">
  <img alt="Platforms" src="https://img.shields.io/badge/platforms-7-orange">
  <img alt="License" src="https://img.shields.io/badge/license-research--only-lightgrey">
</p>

<p align="center">
  🇬🇧 English: <a href="./README.md">README.md</a>
</p>

---

市面上的反检测工具都在帮你**看起来像人**，但没有一个会告诉你**什么时候已经不管用了**。

平台很少直接把你封掉，它先悄悄降权：验证码多了几个、接口还是返回 `200` 但内容变薄了、延迟一点点爬上去、成功率慢慢下滑。等你看到硬邦邦的 `403`，代理费已经烧在垃圾数据上好几天了。

Mirage 两件事都做：

1. **加固** —— 一条命令，给你已有的 MediaCrawler 安装打上五层行为补丁。
2. **可观测** —— 一个软封禁雷达，读五个先行指标，在封禁落地**之前**告诉你该减速了。

> **为什么只有 Mirage 能做第 2 件事：** 反检测浏览器只看得到指纹，代理商只看得到 IP，打码平台只看得到验证码。只有 Mirage 站在那个唯一的位置上——*你注入了什么*、*你发出了什么*、*平台回了什么*，三者同时可见。

## 快速开始

```bash
git clone https://github.com/millennialdreamer/mirage.git && cd mirage

# 1. 先看清楚会改什么 —— 一个字节都不会写
python scripts/apply_hardening.py /path/to/MediaCrawler --dry-run

# 2. 正式执行（每个动到的文件都先备份）
python scripts/apply_hardening.py /path/to/MediaCrawler

# 3. 体检五层加固是不是都还在
python scripts/apply_hardening.py /path/to/MediaCrawler --check
```

后悔了？`--revert` 从备份完整还原。跑了两遍？幂等，零 diff。

核心加固**零第三方依赖**，clone 下来就能跑。

## 雷达 —— Mirage 真正的差异点

```console
$ mirage radar

⚠ Soft-ban radar · account "worker-03"
  Level: WARNING     Risk: 47/100     Samples: 61
  Signals:
    captcha rate:        0.15
    completeness drop:   0.22      ← 返回内容正在悄悄变薄
    latency ratio:       1.9x
    success rate:        0.71
    honeypot hits:       0
  Advice: Clear degradation trend. Halve your rate now, shrink batches,
          pause interactions, and watch whether it recovers.
```

| 信号 | 为什么它领先于封禁 |
|---|---|
| 验证码率 ↑ | 正常应该趋近于 0，一旦抬头说明你已经被怀疑了 |
| **返回完整度 ↓** | **影子封禁的经典特征——照样给你 `200`，只是内容悄悄变薄** |
| 延迟漂移 | 限流最先体现为响应时间中位数往上爬 |
| 蜜罐命中 | 决定性证据。隐藏元素只有自动化程序才会碰 |
| 成功率斜率 | 慢性衰退，跟你自己的基线比，不跟别人比 |

基线跨会话持久化，并且按账号隔离。样本不足 12 个时它拒绝猜测并直说——5 个数据点堆出来的趋势是噪声，不是信号。

## Mirage 站在哪一层

它**不跟**浏览器层的 stealth 方案竞争，而是站在它们上面，补它们够不着的那块。

| | Mirage | undetected-chromedriver / patchright | camoufox 等反检测浏览器 |
|---|:--:|:--:|:--:|
| 工作层面 | 行为 + 运维 | 浏览器驱动 | 浏览器引擎 |
| 给你**已有的**爬虫打补丁 | ✅ | ❌ | ❌ |
| CDP `Runtime.Enable` 泄漏 | ✅ *(靠 patchright)* | ✅ | ✅ |
| Canvas / WebGL 伪造 | ⚠️ 注入级 | ❌ | ✅ 引擎级 |
| 节奏控制、配额、熔断 | ✅ | ❌ | ❌ |
| **软封禁预警** | ✅ | ❌ | ❌ |
| 指纹自洽性审计 | ✅ | ❌ | ⚠️ |

**它们应该一起用。** Mirage 会主动提醒你装 `patchright`——那是一个注入脚本永远够不到的驱动层泄漏。

## 功能

<details open>
<summary><strong>五层加固</strong> —— 一条命令，覆盖 MediaCrawler 全部 7 个平台</summary>

| 层 | 消除的破绽 | 怎么做的 |
|---|---|---|
| **L1** stealth 注入 | `navigator.webdriver` 之类 | CDP 启动时自动注入 |
| **L2** 抖动睡眠 | 固定间隔 = 机器节拍 | 对数正态、右偏，跟真人一样 |
| **L3** 批量 + 安全参数 | 突发暴露、headless | ≤8 条、真实 Chrome、单并发 |
| **L4** 预热 | 一上来就直奔搜索 | 首次查询前停留 3–8 秒 |
| **L5** 鼠标 + 滚动 | 睡眠期间页面完全冻结 | 带缓入缓出的贝塞尔曲线 |

`-p all` 覆盖小红书、抖音、快手、B 站、微博、贴吧、知乎。
</details>

<details>
<summary><strong>设备档案</strong> —— 自洽比单点伪造更重要</summary>

现代检测器不查数值，它查**矛盾**：Windows 的 UA 配 Apple 的 GPU、上海时区配纯美区 locale、主线程 16 核而 worker 里是 4 核。

一个字段一个字段地伪造，只会让你*更*容易被识别，不是更难。Mirage 把所有注入值都从同一份档案推导出来，并且在使用前先审一遍：

```bash
mirage profile worker-03 --emit fp.js
# [device profile seed=worker-03] ✓ self-consistent
#   Windows 11 / Win32 / 12 cores 8GB / 1920x1080 / zh-CN / Asia/Shanghai
#   GPU=ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11...)
```

同一个种子永远产出同一份档案，所以一个账号跨会话保持稳定。Canvas 和音频噪声是**带种子、确定性**的——每次调用都随机这件事本身现在就是破绽，因为检测器会直接渲染两次然后比对哈希。
</details>

<details>
<summary><strong>运维工具</strong> —— canary、上游守卫、验证码钩子</summary>

- `mirage canary <path>` —— 离线体检。补丁还在不在？上游重构把锚点弄坏了没？带退出码，CI 可以卡这个门。全程零网络请求。
- `mirage guard-install <path>` —— 装一个 git hook，当上游 `pull` 悄悄覆盖掉你的加固时警告你。它只警告，绝不背着你改写第三方源码。
- `MirageLoop(on_captcha=...)` —— **Mirage 不破解验证码。** 它只负责检测、交给你自己的打码方案、然后把恢复时机拟人化。解完立刻恢复原速本身就是机器特征。
</details>

<details>
<summary><strong>验证</strong> —— 用第三方的判决，不自己给自己打分</summary>

```bash
python scripts/fingerprint_benchmark.py --botd        # FingerprintJS BotD 判决
python scripts/fingerprint_benchmark.py --detect-url  # 真实检测页 + 完整截图
```

本地那个 7 信号 BotScore 是**相对基线，不是证据**——那是我们自己给自己打的分。可信度排序：第三方判决 > 真实检测页 > 本地分数。
</details>

## 诚实的边界

依赖它之前请先读这段。下面每一条都是*架构*的限制，不是投入不够。

- **注入层有硬天花板。** `toString` 泄漏、执行时序竞态、worker realm 逃逸、属性描述符痕迹，这些从注入的 JavaScript 里根本修不掉。对静态指纹识别大概能扛住（约 70–80%），面对 CreepJS 那种主动探测会明显不够（约 40–50%）。想再往上，需要重新编译引擎——那是本项目有意划在范围之外的事。
- **TLS/JA3 不归我们管。** 那由网络栈决定，JS 碰不到。见 [docs/tls-fingerprint.md](docs/tls-fingerprint.md)。
- **`stealth.min.js` 上游已弃用**（2025 年 2 月），而且它那套随机 canvas 噪声的做法，如今本身已经变成一种检测信号。请装 `patchright`，`mirage doctor` 会一直念叨你。
- **签名层（`a_bogus`、`x-s`、`msToken`）也不归我们管。** 我们直接把你指向仍在维护的库，而不是假装自己逆出来了——见 [docs/signature-layer.md](docs/signature-layer.md)。
- **加固只降低概率，不消除风险。** 只要是自动化，照样可能被抓。

## 文档

| 主题 | |
|---|---|
| 五层加固的原理 | [docs/anti-detection.md](docs/anti-detection.md) |
| 安全使用，以及收到警告之后怎么办 | [docs/safe-usage.md](docs/safe-usage.md) |
| 各平台反爬强度 | [docs/platforms.md](docs/platforms.md) |
| 抖音的四道签名墙 → 对接 F2 | [docs/signature-layer.md](docs/signature-layer.md) |
| TLS / JA3 的边界 | [docs/tls-fingerprint.md](docs/tls-fingerprint.md) |
| App 抓包：mitmproxy 还是 Appium | [docs/app-capture.md](docs/app-capture.md) |
| 海外平台 | [docs/overseas.md](docs/overseas.md) |
| 完整平台覆盖矩阵 | [docs/platform-coverage.md](docs/platform-coverage.md) |
| 互动安全 | [docs/interaction-safety.md](docs/interaction-safety.md) |
| 使用政策与伦理 | [docs/usage-policy.md](docs/usage-policy.md) |

## 命令行

| 命令 | |
|---|---|
| `mirage apply <path> [-p platform] [--dry-run/--check/--revert]` | 应用 / 检查 / 撤销加固 |
| `mirage radar [--account X] [--reset]` | 软封禁预警 |
| `mirage profile <seed> [--emit file]` | 生成并审计设备档案 |
| `mirage canary <path>` | 离线加固体检 |
| `mirage guard-install / guard-uninstall <path>` | 防上游覆盖的 git hook |
| `mirage doctor` | 环境自检 |
| `mirage verify` / `mirage benchmark` | 指纹检查 *(这两个由你自己手动跑)* |

## 安装

```bash
pip install -e .                    # 核心，零第三方依赖
pip install -e ".[browser]"         # 额外装 patchright，用于指纹验证
```

Python 3.9+。你需要一个可用的 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 安装——Mirage 是给它做加固的，它自己不是爬虫。

## 开发

```bash
bash scripts/ci.sh                              # pytest + ruff + mypy
git config core.hooksPath .githooks             # 每次 push 前自动跑 CI
```

对第三方源码的修改走「原子写入 → AST 校验 → 失败回滚」。回归测试拿真实的正则锚点去打一个真实的 MediaCrawler checkout（自动探测，也可以设 `MIRAGE_TEST_MEDIACRAWLER`）；没有的话会干净地跳过。本仓库不 vendor 任何第三方源码。

## 适用范围与责任

**仅供学习、研究和个人测试。** 请用小号。把速率压低。

把话说白：绝大多数平台的服务条款本来就禁止自动化访问和自动化互动。这个项目不会假装照着清单做一遍就没事了。**用不用、用在哪、以及后果，都由你自己判断、自己承担。** 它提供的是技术和边界，不是对任何特定用途的背书。

互动引擎默认 `dry_run=True`，遇到验证码就停而不是尝试破解，每日配额卡在比重度真人用户还低的水平。详见 [docs/usage-policy.md](docs/usage-policy.md)。

## 许可

研究与非商业用途 —— 见 [LICENSE](LICENSE)。
