# 全平台覆盖矩阵（2026 穷尽版）—— 海内外主流全盘

> Mirage 的**行为层加固**只直接管 MediaCrawler 的 7 个平台。这张矩阵把**海内外主流全盘一遍**（含长尾），
> 每个给出：反爬关键、2026 **最新活维护**的现成栈、新鲜度、Mirage 关系。
> **方法论收敛（再次印证）**：不管哪个平台，答案都是——**找活维护栈桥接 + `curl_cffi` 补 TLS + `pacing` 控节奏**，绝不从零逆向。
> 可运行桥接模板见 [`examples/bridges_quickref.py`](../examples/bridges_quickref.py)（只给 clean-API 活维护栈；偏旧库不写虚模板）。

## 关系三档
**① 直接加固**（Mirage 五层生效，MediaCrawler 7 平台）｜**② 桥接·指路牌**（有墙、指向活维护栈）｜**③ 超边界**（账号池/App/工作室级）

## 国内

| 类目 | 平台 | 反爬关键 | 2026 现成栈 | 新鲜度 | 关系 |
|------|------|---------|-------------|--------|------|
| 内容 | 小红书/抖音/快手/B站/微博/贴吧/知乎 | 行为+签名(x-s/a_bogus/x-zse-96) | MediaCrawler + Mirage 加固 | ✅活 | ① |
| 电商 | 淘宝/天猫/京东/1688 | mtop + x-sign | [SpiderCrackDemo](https://github.com/xinxianren/SpiderCrackDemo) / [ECommerceCrawlers](https://github.com/DropsDevopsOrg/ECommerceCrawlers) | ⚠️偏旧2022 | ② |
| 电商 | 拼多多 | anti_content + AccessToken | [banduoba/pinduoduo](https://github.com/banduoba/pinduoduo-1) / [Crack-JS-Spider](https://github.com/LoseNine/Crack-JS-Spider) | ⚠️偏旧 | ② |
| 电商 | 闲鱼 | 登录态+风控 | [ECommerceCrawlers](https://github.com/DropsDevopsOrg/ECommerceCrawlers) | ⚠️偏旧 | ② |
| 本地生活 | 美团/外卖 | mtgsig + _token(2次加密) | [SpiderCrackDemo](https://github.com/xinxianren/SpiderCrackDemo) / [xzh0723/MeiTuan](https://github.com/xzh0723/MeiTuan) | ⚠️偏旧·高改版 | ② |
| 本地生活 | 大众点评 | **CSS字体加密**+坐标 | SpiderCrackDemo + `fontTools` 解 WOFF | 方法稳定 | ② |
| 音乐 | 网易云/QQ/酷狗/酷我/咪咕 | 加密url+版权 | [musicdl](https://github.com/CharlesPikachu/musicdl)(数十平台) / [go-music-dl](https://github.com/guohuiyuan/go-music-dl) | ✅活维护 | ② |
| 长视频 | 爱奇艺/腾讯/优酷/芒果 | m3u8+加密 | [yt-dlp](https://github.com/yt-dlp/yt-dlp) / [webvideo-downloader](https://github.com/jaysonlong/webvideo-downloader) | ✅活维护 | ② |
| 资讯 | 今日头条/搜狐 | 签名+风控 | [ECommerceCrawlers](https://github.com/DropsDevopsOrg/ECommerceCrawlers) / [crawlProject](https://github.com/xishandong/crawlProject) | ⚠️偏旧 | ② |
| 社区/影音 | 豆瓣 | 限流+风控 | ECommerceCrawlers | ⚠️偏旧 | ② |
| 招聘 | boss直聘/拉勾 | zp_token | [Crack-JS-Spider](https://github.com/LoseNine/Crack-JS-Spider) | ⚠️偏旧 | ② |
| 微信生态 | 公众号/视频号/文章 | 登录态+风控 | [wechat-article-exporter](https://github.com/wechat-article/wechat-article-exporter) / [wechat-download-api](https://github.com/tmwgsicp/wechat-download-api) | ✅活维护·最省心 | ② |
| 地图/本地 | 高德/百度地图 | 签名+配额 | **官方开放平台 API**（优先）/ Just One API | ✅官方 | ② |

## 海外

| 类目 | 平台 | 反爬关键 | 2026 现成栈 | 新鲜度 | 关系 |
|------|------|---------|-------------|--------|------|
| 视频 | YouTube + 1800 站 | —— | [yt-dlp](https://github.com/yt-dlp/yt-dlp) | ✅日更 | ② 一把梭 |
| 社交 | X / IG / TikTok | 见 [overseas.md](overseas.md) | twscrape / [instagrapi](https://github.com/subzeroid/instagrapi) / TikTok-Api | ✅/⚠️ | ② |
| 论坛 | Reddit | OAuth+限流100/min | [PRAW](https://github.com/praw-dev/praw) 官方 | ✅活维护 | ② 官方API |
| IM | Telegram | MTProto | [Telethon](https://github.com/LonamiWebs/Telethon) 官方 | ✅活维护 | ② 官方库 |
| 图集 | Pinterest | 登录态 | [gallery-dl](https://github.com/mikf/gallery-dl) + topic repos | ✅活 | ② |
| 新社交 | Threads(Meta) | 背景请求签名 | Playwright + 背景请求捕获（[Scrapfly 法](https://scrapfly.io/blog/posts/how-to-scrape-threads)），无 clean lib | ⚠️需自写 | ②/③ |
| 地图评价 | Google Maps/Yelp | DataDome/Cloudflare | [google-reviews-scraper-pro](https://github.com/georgekhananaev/google-reviews-scraper-pro) / SeleniumBase CDP + **curl_cffi** | ✅活维护 | ② |
| 电商 | Amazon reviews | 风控+验证码 | bs4 脚本(脆) / 商用 API | ⚠️脆 | ②/③ |
| 职业 | LinkedIn | 强认证+封号 | 账号池 + 商用 API（11 家仅 4 家>80%） | 🔴 | ③ 超边界 |
| 短内容 | Snapchat/Quora | 强风控 | 弱维护/无稳定开源 | 🔴 | ③ 超边界 |
| App（任意） | 各家 App | SSL pinning+签名 | 见 [app-capture.md](app-capture.md)（frida/Appium） | —— | ③ 超边界 |

## 2026 值得知道的通用武器
- **[Scrapling](https://github.com/D4Vinci/Scrapling)**（25k★ 崛起）：自愈式自适应解析 + 反爬绕过 + AI，页面结构变了能自适应，适合长尾平台省维护。
- **curl_cffi**：贯穿签名层/海外/Google-Yelp 的 TLS 伪装底座（`impersonate="chrome"`），一招通用。
- **snscrape**：多平台社交，但 **X 支持 2023 后基本挂**，慎用；X 现用 twscrape。

## 诚实提醒（别被"有库"骗）
1. **国内电商/本地生活/招聘 crack 库普遍偏旧**（部分停 2022），远不如 yt-dlp/musicdl/PRAW/Telethon 活跃——是"参考起点"，用前看 commit 日期、找新 fork，或准备自维护。淘宝/美团改版极快。
2. **最省心的几类**：长视频/音乐（yt-dlp/musicdl）、微信公众号（wechat-article-exporter）、Reddit（PRAW）、Telegram（Telethon）——都活维护、API 干净。
3. **地图优先走官方开放平台 API**（高德/百度/Google），别硬爬。
4. **LinkedIn/Snapchat/Quora/Amazon 深度 = 超边界**，2026 商用 API 都只 4/11 家过 80%，别指望开源单兵。

## 一句话
**海内外主流全盘：MediaCrawler 7 平台 Mirage 直接加固；音乐/长视频/微信/Reddit/Telegram 有活维护 clean 栈直接桥接；电商/本地生活/招聘桥接偏旧 crack 库（自备维护）；LinkedIn/App 群控超边界。curl_cffi 补 TLS + pacing + 找活维护栈——一套通解全平台。**
