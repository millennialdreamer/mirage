# 海外平台：两层地图 + pacing 方法论 + Mirage 的边界

> 结论先行：海外平台**不在 MediaCrawler / Mirage 的加固范围**（不同框架、不同栈）。这篇是
> 2026 实证的**指路牌 + 方法论**。核心分野：**公开内容用 yt-dlp（零账号风险、最稳）；
> 要账号态的（X/IG/TikTok）才是难点，且它们全栽在同一处——请求节奏（pacing）**。

## 两层：先分清"要不要账号"

| 层 | 平台 / 库 | 账号 | 封号风险 | 难度 |
|----|-----------|------|---------|------|
| **A 公开内容** | [yt-dlp](https://github.com/yt-dlp/yt-dlp)（YouTube + 1800 站，日更活跃）/ [gallery-dl](https://github.com/mikf/gallery-dl)（图集） | 不要 | 几乎无 | ✅ 直接用，最稳 |
| **B 账号态** | [twscrape](https://github.com/vladkens/twscrape)(X) / [instaloader](https://github.com/instaloader/instaloader)(IG) / [TikTok-Api](https://github.com/davidteather/TikTok-Api)(TikTok) | 要 cookie / 账号 | **高** | ⚠️ 账号 + 代理 + pacing |

**先问自己**：只要公开视频 / 图 → 层 A，yt-dlp 一把梭，别碰账号。要账号态数据（关注 / 私有 / 互动）→ 层 B，做好养号 + 重投入准备。

## 层 B 的真正难点：所有账号库都栽在 pacing

2026 实证——X / IG / TikTok 三家都在**同一处**卡人：
- **X（twscrape）**：X 同时盯 IP 信誉 / 登录地理 / **请求节奏** / 跨账号模式；任一错 → 限流 / 影子封 / 永封。原话：*"撞限流后立刻轮换接着猛打，这个模式本身就是信号"* → 要**指数退避**，不是硬轮换。twscrape 内置限流处理 + 可选 **curl-cffi TLS 伪装**（和我们签名层同一招）。
- **IG（instaloader）**：单 session，重用即触发封号；用户一直求"能自定义限流"（issue #1922）。
- **TikTok（TikTok-Api）**：跑 Playwright + 要 ms_token（DevTools 里抓）+ 代理 + `sleep_after` 等 msToken 生成。**和抖音 App 同源**（ms_token）。

**共性 = pacing 决定生死**：抖动间隔 + 每日配额 + 指数退避 + 熔断。这恰好是 Mirage 行为层 [`interaction_policy.py`](../scripts/interaction_policy.py) 已有的 L2/L3/L4 方法论——**可抽象成平台无关的 pacing 中间件**包在这些账号库外面（twscrape 已自带、instaloader 最缺）。

## TLS 一致性（呼应签名层）

twscrape 用 **curl-cffi** 做 TLS 伪装——和 [`docs/tls-fingerprint.md`](tls-fingerprint.md) / [`docs/signature-layer.md`](signature-layer.md) 推荐的**完全同一招**。不管国内抖音还是海外 X，传输层 JA3 的解都是 curl_cffi。三个深坑（签名 / App / 海外）在这里收敛成一套方法论。

## Mirage 的边界

- Mirage 加固网页版 MediaCrawler 行为层；海外是另一套库。**Mirage 不接管**。
- 能借的是**方法论**：层 B 账号库怕封 → 用 Mirage 的 pacing 思路（抖动 / 配额 / 退避 / 熔断）+ 住宅代理 + 养号。
- 能给的是**指路牌**：公开内容 yt-dlp、X twscrape、IG instaloader、TikTok TikTok-Api。

## 一句话

**海外两层：公开内容 yt-dlp 一把梭（零风险）；账号态 X/IG/TikTok 全栽在 pacing（抖动+配额+指数退避+熔断，和 Mirage 行为层同源）+ curl_cffi 补 TLS（和签名层同源）。Mirage 给指路牌 + 方法论，不接管。**
