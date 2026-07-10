# 全平台覆盖矩阵（2026 实证）—— Mirage 直接加固什么、其余指向哪

> Mirage 的**行为层加固**只直接管 MediaCrawler 的 7 个平台（小红书/抖音/快手/B站/微博/贴吧/知乎）。
> 但市面主流远不止这些。这张矩阵把**其余主流平台**也盘清楚：各自的反爬类型、2026 活维护的现成栈、以及 Mirage 与它的关系。
> **方法论收敛**：不管哪个平台，答案都是同一套——**找到活维护的现成栈桥接它 + curl_cffi 补 TLS + pacing 控节奏**，绝不自己从零逆向。

## Mirage 与各平台的三种关系

| 关系 | 含义 | 覆盖谁 |
|------|------|--------|
| **① 直接加固** | Mirage 五层行为层加固直接生效 | MediaCrawler 7 平台（xhs/dy/ks/bili/wb/tieba/zhihu）|
| **② 签名桥接·指路牌** | 有签名墙、Mirage 不接管，指向活维护 crack 栈 | 淘宝/拼多多/美团/知乎签名/boss直聘… |
| **③ 超边界** | 账号池 / App / 工作室级投入，Mirage 只诚实说清 | LinkedIn/Amazon/FB、App 群控… |

## 覆盖矩阵

| 类目 | 平台 | 反爬关键 | 2026 现成栈（桥接对象） | 新鲜度 | Mirage 关系 |
|------|------|---------|------------------------|--------|-------------|
| 国内内容 | 小红书/抖音/快手/B站/微博/贴吧/知乎 | 行为+签名(x-s/a_bogus/x-zse-96) | MediaCrawler 本体 + Mirage 加固 | 活 | **① 直接加固** |
| 国内电商 | 淘宝/天猫/京东/1688 | `mtop` 接口 + `x-sign` | [SpiderCrackDemo](https://github.com/xinxianren/SpiderCrackDemo) / [ECommerceCrawlers](https://github.com/DropsDevopsOrg/ECommerceCrawlers) | ⚠️ 偏旧(部分2022) | ② 桥接 |
| 国内电商 | 拼多多 | `anti_content`(Get_c/i/s/u) + AccessToken | [banduoba/pinduoduo](https://github.com/banduoba/pinduoduo-1) / [Crack-JS-Spider](https://github.com/LoseNine/Crack-JS-Spider) | ⚠️ 偏旧 | ② 桥接 |
| 本地生活 | 美团/美团外卖 | `mtgsig` + `_token`(2次加密+gzip) | [SpiderCrackDemo](https://github.com/xinxianren/SpiderCrackDemo) / [xzh0723/MeiTuan](https://github.com/xzh0723/MeiTuan) | ⚠️ 偏旧·高改版 | ② 桥接 |
| 本地生活 | 大众点评 | **CSS 字体加密** + 坐标加密 | SpiderCrackDemo + `fontTools` 解 WOFF 字体映射 | 方法稳定 | ② 桥接 |
| 招聘 | boss直聘/拉勾 | `zp_token` | [Crack-JS-Spider](https://github.com/LoseNine/Crack-JS-Spider) | ⚠️ 偏旧 | ② 桥接 |
| 微信生态 | 公众号/文章/阅读量 | 登录态 + 风控 | [wechat-article-exporter](https://github.com/wechat-article/wechat-article-exporter)(在线/docker) / [wechat-download-api](https://github.com/tmwgsicp/wechat-download-api)(RSS+IP池) / [striver-ing/wechat-spider](https://github.com/striver-ing/wechat-spider) | ✅ 活维护 | ② 桥接·直接用 |
| 海外内容 | YouTube/X/IG/TikTok | 见 [overseas.md](overseas.md) | yt-dlp / twscrape / instaloader / TikTok-Api | ✅/⚠️ | ② 见海外篇 |
| 海外社交 | Reddit | OAuth + 限流(100/min) | [PRAW](https://github.com/praw-dev/praw) 官方 API wrapper | ✅ 活维护(2026) | ② 桥接·官方 API |
| 海外社交/电商 | LinkedIn/Amazon/Facebook | 强认证 + 账号封锁 | 账号池 + 商用 scraping API（Proxyway 测 11 家仅 4 家 >80% 成功率） | 难 | **③ 超边界** |
| App（任意） | 抖音/小红书 App 等 | SSL pinning + 签名 | 见 [app-capture.md](app-capture.md)（frida/Appium） | —— | **③ 超边界** |

## 诚实提醒（别被"有现成库"骗了）

1. **国内电商/本地生活的 crack 库普遍偏旧**（部分参数停在 2022），远不如 F2/yt-dlp/PRAW 活跃。淘宝 `x-sign`、美团 `mtgsig` 改版极快——**这些库是"参考起点"不是"保证可用"**，用前先看 commit 日期、找更新的 fork，或准备自己维护。
2. **微信公众号栈最省心**（多个活维护、甚至在线/docker 开箱即用），是这批里最容易的。
3. **大众点评的 CSS 字体加密**方法稳定（fontTools 解字体映射），不随参数改版天天变，值得优先。
4. **LinkedIn/Amazon/Facebook 是超边界**——2026 商用 scraping API 都只有 4/11 家能过 80%，别指望开源单兵搞定，要么账号池要么买 API。

## 一句话

**市面主流全盘一遍，答案还是那套：MediaCrawler 7 平台 Mirage 直接加固；其余带签名墙的（电商/本地生活/招聘/微信/知乎）桥接活维护 crack 栈（注意国内电商库偏旧、要自备维护）；LinkedIn/Amazon/App 群控是超边界。不自逆、找现成栈、curl_cffi 补 TLS、pacing 控节奏——一套通解。**
