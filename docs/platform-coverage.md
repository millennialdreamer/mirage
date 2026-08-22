# Full Platform Coverage Matrix (2026 Exhaustive Edition) — Mainstream Domestic and Overseas, Entire Board

> Mirage's **behavioral-layer hardening** only directly manages MediaCrawler's 7 platforms. This matrix covers **all mainstream domestic and overseas platforms in one pass** (including long tail),
> each with: anti-crawling key, **latest actively maintained** off-the-shelf stack as of 2026, freshness, Mirage relationship.
> **Freshness verified by multiple third parties + GitHub fact-checking** (actively maintained projects still releasing in 2026-06/07; marked 🔴 are dead/high-risk, don't step on them).
> **Methodology convergence (confirmed again)**: find actively maintained stack bridges + `curl_cffi` to supplement TLS + `pacing` to control rhythm, never reverse from scratch.
> Runnable bridge template see [`examples/bridges_quickref.py`](../examples/bridges_quickref.py) (only gives clean-API actively maintained stacks).

## Three Relationship Tiers
**① Direct hardening** (Mirage's five layers take effect, MediaCrawler 7 platforms) | **② Bridge·signpost** (has a wall, points to actively maintained stacks) | **③ Beyond boundary** (account pool/App/studio-level)

## Domestic

| Category | Platform | Anti-crawling key | 2026 Off-the-shelf stack | Freshness | Relationship |
|------|------|---------|-------------|--------|------|
| Content | Xiaohongshu/Douyin/Kuaishou/Bilibili/Weibo/Tieba/Zhihu | Behavior + signature (x-s/a_bogus/x-zse-96) | MediaCrawler + Mirage hardening | ✅ active | ① |
| E-commerce | Taobao/Tmall/JD/1688 | mtop + x-sign | [SpiderCrackDemo](https://github.com/xinxianren/SpiderCrackDemo) / [ECommerceCrawlers](https://github.com/DropsDevopsOrg/ECommerceCrawlers) | 🔴 demo likely dead (≤2022)·principle reference only | ② |
| E-commerce | Pinduoduo | anti_content + AccessToken | [banduoba/pinduoduo](https://github.com/banduoba/pinduoduo-1) / [Crack-JS-Spider](https://github.com/LoseNine/Crack-JS-Spider) | 🔴 likely dead·principle reference only | ② |
| E-commerce | Xianyu | Login state + risk control | ECommerceCrawlers (e-commerce collection, scraping Xianyu is a stretch) | 🔴 discontinued (~2021) | ②/③ |
| Local life | Meituan/Food delivery | mtgsig + _token (2-layer encryption) | [SpiderCrackDemo](https://github.com/xinxianren/SpiderCrackDemo) / [xzh0723/MeiTuan](https://github.com/xzh0723/MeiTuan) | 🔴 mtgsig heavily revised·demos mostly dead | ② |
| Local life | Dianping | **CSS font encryption**+coordinates | SpiderCrackDemo + `fontTools` to decode WOFF | ✅ font method stable (doesn't change daily with parameters) | ② |
| Music | NetEase Cloud Music/QQ Music/Kugou/Kuwo/Migu | Encrypted URL + copyright | [musicdl](https://github.com/CharlesPikachu/musicdl)(2026-07 v2.13 active, dozens of platforms) / [go-music-dl](https://github.com/guohuiyuan/go-music-dl) | ✅ actively maintained | ② |
| Long video | iQiyi/Tencent (partial)·Youku/Mango (weak DRM) | m3u8 + DRM | [yt-dlp](https://github.com/yt-dlp/yt-dlp) / [webvideo-downloader](https://github.com/jaysonlong/webvideo-downloader) | ✅ active·but weak support for domestic DRM | ② |
| News | Toutiao/Sohu | Signature + risk control | [crawlProject](https://github.com/xishandong/crawlProject)(JS reverse collection, relatively new) | ⚠️ reference-level | ② |
| Community/Movie | Douban | Rate limiting + risk control | Generic requests + slow speed (Douban anti-crawling is relatively weak) | ⚠️ mostly self-written | ② |
| Recruitment | BOSS Zhipin/Lagou/**Zhaopin/51job/Maimai** | zp_token etc. | [Crack-JS-Spider](https://github.com/LoseNine/Crack-JS-Spider)(zp_token) / each requires own reverse | 🔴 demos outdated·Maimai strictest | ②/③ |
| WeChat ecosystem | Official Account/Articles (**Channels harder**) | Login state + risk control | [wechat-article-exporter](https://github.com/wechat-article/wechat-article-exporter) / [wechat-download-api](https://github.com/tmwgsicp/wechat-download-api) | ✅ Official Account articles easiest·Channels still hard | ② |
| Maps/Local | AutoNavi/Baidu Maps | Signature + quota | **Official open platform API** | ⚠️ official API low quota/requires qualifications/does not return original comments — use if sufficient, don't force crawling (high legal risk) | ② |

## Overseas

| Category | Platform | Anti-crawling key | 2026 Off-the-shelf stack | Freshness | Relationship |
|------|------|---------|-------------|--------|------|
| Video | YouTube + 1800 sites | — | [yt-dlp](https://github.com/yt-dlp/yt-dlp) | ✅ daily updates | ② one-shot solution |
| Social | X / IG / TikTok | see [overseas.md](overseas.md) | twscrape / [instagrapi](https://github.com/subzeroid/instagrapi)(2026-07 v2.18 active) / TikTok-Api | ✅/⚠️ | ② |
| Forum | Reddit | OAuth + rate limit 100/min | [PRAW](https://github.com/praw-dev/praw) official | ✅ actively maintained | ② official API |
| IM | Telegram | MTProto | [Telethon](https://github.com/LonamiWebs/Telethon) official | ✅ active·but first login requires interactive verification code | ② official library |
| Image gallery | Pinterest | Login state | [gallery-dl](https://github.com/mikf/gallery-dl)(2026-06 v1.32.5 active·main dev moved to Codeberg) | ✅ active | ② |
| Community | **Discord** | Token + risk control | discord.py(bot) / self-built bot | ✅ active (official bot) | ② |
| Audio | **Spotify** | OAuth | spotipy (official API, playlists/podcast metadata) | ✅ active·official | ② |
| Emerging social | Threads (Meta) | Background request signature | Playwright + background request capture, no clean library | ⚠️ requires self-write | ②/③ |
| Map reviews | Google Maps/Yelp | DataDome/Cloudflare | [google-reviews-scraper-pro](https://github.com/georgekhananaev/google-reviews-scraper-pro) / SeleniumBase CDP + **curl_cffi** | ✅ actively maintained | ② |
| Professional | **LinkedIn** | Strong auth + account ban | Account pool + commercial API | 🔴 **violates ToS·high legal risk** | ③ beyond boundary |
| E-commerce | Amazon reviews | Risk control + CAPTCHA | bs4 script (fragile) / commercial API | 🔴 **violates ToS·IP ban extremely strict** | ③ beyond boundary |
| Social | **Facebook** (pages/groups) | Strong auth + risk control | Account + Playwright / commercial API | 🔴 high risk | ③ beyond boundary |
| Short content | Snapchat/Quora | Strong risk control | No stable open source | 🔴 beyond boundary | ③ |
| App (any) | Any App | SSL pinning + signature | see [app-capture.md](app-capture.md) (frida/Appium) | — | ③ beyond boundary |

## General Weapons Worth Knowing in 2026
- **[Scrapling](https://github.com/D4Vinci/Scrapling)** (25k★ rising): self-healing adaptive parsing + anti-bot bypass + AI, adapts when page structure changes, suitable for long-tail platforms to reduce maintenance.
- **curl_cffi**: the TLS camouflage base throughout the signature layer/overseas/Google-Yelp (`impersonate="chrome"`), one trick for all.
- **snscrape**: once a multi-platform social scraping tool, **basically abandoned after 2023** (not just X broken) — don't count on it anymore; use twscrape for X, others see this matrix.

## Honest Reminders (reviewed by multiple parties + fact-checked — don't be fooled by "there's a library")
1. **Domestic e-commerce/local life/recruiting crack demos are basically dead** (≤2022, marked 🔴): Taobao x-sign, Meituan mtgsig, Pinduoduo anti_content iterated many rounds in 2023-2026; old demos will almost certainly fail when used directly — **treat them only as principle references**; either find latest fork, reverse yourself (high cost), or use Scrapling adaptive to brute force.
2. **Truly worry-free and alive** (GitHub verified still releasing in 2026-06/07): long video/music (yt-dlp/musicdl), WeChat Official Account articles (wechat-article-exporter), Reddit (PRAW), Telegram (Telethon), IG (instagrapi), image galleries (gallery-dl), Google reviews (curl_cffi). These are the only ones you can start with directly.
3. **Don't force deep maps/career/e-commerce**: AutoNavi/Baidu Maps use official API (low quota but compliant); LinkedIn/Amazon/Facebook clearly **violate ToS, high legal risk**, account bans extremely strict, don't expect open-source single-soldier, these are beyond boundary.
4. **App deep data (Douyin/Xiaohongshu App data)** = another stack with frida/Appium, see app-capture.md, studio-level investment.

## One Sentence
**Full coverage of mainstream domestic and overseas: MediaCrawler's 7 platforms are directly hardened by Mirage; music/long video/WeChat Official Account articles/Reddit/Telegram/IG/image galleries have actively maintained clean stacks to bridge directly; old crack demos for domestic e-commerce/local life/recruiting are likely dead (only principle references); LinkedIn/Amazon/Facebook/App group control are ToS-violating high-risk beyond boundary. curl_cffi + pacing + find actively maintained stacks — one universal solution, but freshness and risk are honestly marked for every platform.**