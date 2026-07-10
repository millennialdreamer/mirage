# 全平台覆盖矩阵（2026 穷尽版）—— 海内外主流全盘

> Mirage 的**行为层加固**只直接管 MediaCrawler 的 7 个平台。这张矩阵把**海内外主流全盘一遍**（含长尾），
> 每个给出：反爬关键、2026 **最新活维护**的现成栈、新鲜度、Mirage 关系。
> **新鲜度经三方多方审 + GitHub 事实核实**（活维护的看到 2026-06/07 仍发版；标🔴的是已失效/高风险，别踩）。
> **方法论收敛（再次印证）**：找活维护栈桥接 + `curl_cffi` 补 TLS + `pacing` 控节奏，绝不从零逆向。
> 可运行桥接模板见 [`examples/bridges_quickref.py`](../examples/bridges_quickref.py)（只给 clean-API 活维护栈）。

## 关系三档
**① 直接加固**（Mirage 五层生效，MediaCrawler 7 平台）｜**② 桥接·指路牌**（有墙、指向活维护栈）｜**③ 超边界**（账号池/App/工作室级）

## 国内

| 类目 | 平台 | 反爬关键 | 2026 现成栈 | 新鲜度 | 关系 |
|------|------|---------|-------------|--------|------|
| 内容 | 小红书/抖音/快手/B站/微博/贴吧/知乎 | 行为+签名(x-s/a_bogus/x-zse-96) | MediaCrawler + Mirage 加固 | ✅活 | ① |
| 电商 | 淘宝/天猫/京东/1688 | mtop + x-sign | [SpiderCrackDemo](https://github.com/xinxianren/SpiderCrackDemo) / [ECommerceCrawlers](https://github.com/DropsDevopsOrg/ECommerceCrawlers) | 🔴 demo 大概率失效(≤2022)·仅原理参考 | ② |
| 电商 | 拼多多 | anti_content + AccessToken | [banduoba/pinduoduo](https://github.com/banduoba/pinduoduo-1) / [Crack-JS-Spider](https://github.com/LoseNine/Crack-JS-Spider) | 🔴 大概率失效·仅原理参考 | ② |
| 电商 | 闲鱼 | 登录态+风控 | ECommerceCrawlers（电商合集，抓闲鱼较牵强） | 🔴 停更(~2021) | ②/③ |
| 本地生活 | 美团/外卖 | mtgsig + _token(2次加密) | [SpiderCrackDemo](https://github.com/xinxianren/SpiderCrackDemo) / [xzh0723/MeiTuan](https://github.com/xzh0723/MeiTuan) | 🔴 mtgsig 高改版·demo 多失效 | ② |
| 本地生活 | 大众点评 | **CSS字体加密**+坐标 | SpiderCrackDemo + `fontTools` 解 WOFF | ✅ 字体法稳定(不随参数天天变) | ② |
| 音乐 | 网易云/QQ/酷狗/酷我/咪咕 | 加密url+版权 | [musicdl](https://github.com/CharlesPikachu/musicdl)(2026-07 v2.13 活跃,数十平台) / [go-music-dl](https://github.com/guohuiyuan/go-music-dl) | ✅活维护 | ② |
| 长视频 | 爱奇艺/腾讯(部分)·优酷/芒果(DRM差) | m3u8 + DRM | [yt-dlp](https://github.com/yt-dlp/yt-dlp) / [webvideo-downloader](https://github.com/jaysonlong/webvideo-downloader) | ✅活·但国产 DRM 支持弱 | ② |
| 资讯 | 今日头条/搜狐 | 签名+风控 | [crawlProject](https://github.com/xishandong/crawlProject)(JS逆向合集,较新) | ⚠️ 参考级 | ② |
| 社区/影音 | 豆瓣 | 限流+风控 | 通用请求 + 慢速(豆瓣反爬相对弱) | ⚠️ 自写为主 | ② |
| 招聘 | boss直聘/拉勾/**智联/前程无忧/脉脉** | zp_token 等 | [Crack-JS-Spider](https://github.com/LoseNine/Crack-JS-Spider)(zp_token) / 各自逆向 | 🔴 demo 偏旧·脉脉最严 | ②/③ |
| 微信生态 | 公众号/文章(**视频号更难**) | 登录态+风控 | [wechat-article-exporter](https://github.com/wechat-article/wechat-article-exporter) / [wechat-download-api](https://github.com/tmwgsicp/wechat-download-api) | ✅ 公众号文章最省心·视频号仍难 | ② |
| 地图/本地 | 高德/百度地图 | 签名+配额 | **官方开放平台 API** | ⚠️ 官方 API 配额低/需资质/不返原始评论——够用则用，别硬爬(法律风险高) | ② |

## 海外

| 类目 | 平台 | 反爬关键 | 2026 现成栈 | 新鲜度 | 关系 |
|------|------|---------|-------------|--------|------|
| 视频 | YouTube + 1800 站 | —— | [yt-dlp](https://github.com/yt-dlp/yt-dlp) | ✅日更 | ② 一把梭 |
| 社交 | X / IG / TikTok | 见 [overseas.md](overseas.md) | twscrape / [instagrapi](https://github.com/subzeroid/instagrapi)(2026-07 v2.18 活跃) / TikTok-Api | ✅/⚠️ | ② |
| 论坛 | Reddit | OAuth+限流100/min | [PRAW](https://github.com/praw-dev/praw) 官方 | ✅活维护 | ② 官方API |
| IM | Telegram | MTProto | [Telethon](https://github.com/LonamiWebs/Telethon) 官方 | ✅活·但首次登录要交互验证码 | ② 官方库 |
| 图集 | Pinterest | 登录态 | [gallery-dl](https://github.com/mikf/gallery-dl)(2026-06 v1.32.5 活跃·主开发迁 Codeberg) | ✅活 | ② |
| 社区 | **Discord** | Token+风控 | discord.py(bot) / 自建 bot | ✅活(官方bot) | ② |
| 音频 | **Spotify** | OAuth | spotipy(官方API,歌单/播客元数据) | ✅活·官方 | ② |
| 新社交 | Threads(Meta) | 背景请求签名 | Playwright + 背景请求捕获，无 clean lib | ⚠️需自写 | ②/③ |
| 地图评价 | Google Maps/Yelp | DataDome/Cloudflare | [google-reviews-scraper-pro](https://github.com/georgekhananaev/google-reviews-scraper-pro) / SeleniumBase CDP + **curl_cffi** | ✅活维护 | ② |
| 职业 | **LinkedIn** | 强认证+封号 | 账号池 + 商用 API | 🔴 **违反 ToS·高法律风险** | ③ 超边界 |
| 电商 | Amazon reviews | 风控+验证码 | bs4 脚本(脆) / 商用 API | 🔴 **违 ToS·封 IP 极严** | ③ 超边界 |
| 社交 | **Facebook**(主页/群组) | 强认证+风控 | 账号 + Playwright / 商用 API | 🔴 高风险 | ③ 超边界 |
| 短内容 | Snapchat/Quora | 强风控 | 无稳定开源 | 🔴 超边界 | ③ |
| App（任意） | 各家 App | SSL pinning+签名 | 见 [app-capture.md](app-capture.md)（frida/Appium） | —— | ③ 超边界 |

## 2026 值得知道的通用武器
- **[Scrapling](https://github.com/D4Vinci/Scrapling)**（25k★ 崛起）：自愈式自适应解析 + 反爬绕过 + AI，页面结构变了能自适应，适合长尾平台省维护。
- **curl_cffi**：贯穿签名层/海外/Google-Yelp 的 TLS 伪装底座（`impersonate="chrome"`），一招通用。
- **snscrape**：曾经的多平台社交神器，**2023 后整体基本废弃**（不只 X 挂）——别再指望它；X 用 twscrape、其余见本矩阵。

## 诚实提醒（经多方审 + 事实核实，别被"有库"骗）
1. **国内电商/本地生活/招聘的 crack demo 基本已死**（≤2022，标🔴）：淘宝 x-sign、美团 mtgsig、拼多多 anti_content 2023-2026 迭代多轮，老 demo 拿来即用几乎必失败——**只当原理参考**，要么找最新 fork、要么自己逆向（成本高）、要么用 Scrapling 自适应硬扛。
2. **真正省心且活的**（GitHub 核实 2026-06/07 仍发版）：长视频/音乐(yt-dlp/musicdl)、微信公众号文章(wechat-article-exporter)、Reddit(PRAW)、Telegram(Telethon)、IG(instagrapi)、图集(gallery-dl)、Google 评价(curl_cffi)。这些才是能直接上手的。
3. **地图/职业/电商深度别硬来**：高德/百度地图走官方 API(配额低但合规)；LinkedIn/Amazon/Facebook 明确**违反 ToS、高法律风险**，账号封锁极严，别指望开源单兵，属超边界。
4. **App 深度（抖音/小红书 App 数据）** = frida/Appium 另一套栈，见 app-capture.md，工作室级投入。

## 一句话
**海内外主流全盘：MediaCrawler 7 平台 Mirage 直接加固；音乐/长视频/微信公众号/Reddit/Telegram/IG/图集有活维护 clean 栈直接桥接；国内电商/本地生活/招聘的老 crack demo 大概率已死(只当原理参考)；LinkedIn/Amazon/Facebook/App 群控是违 ToS 高风险超边界。curl_cffi + pacing + 找活维护栈——一套通解，但对每个平台都诚实标了新鲜度和风险。**
