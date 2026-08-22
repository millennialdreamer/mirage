# Overseas platforms: two-layer map + pacing methodology + Mirage's boundaries

> Conclusion first: overseas platforms are **outside MediaCrawler / Mirage's hardening scope** (different framework, different stack). This is a 2026 evidence-based **signpost + methodology**. Core divide: **public content via yt-dlp (zero account risk, most stable); account-state platforms (X/IG/TikTok) are where it gets hard, and they all fail at the same place—request pacing**.

## Two layers: first distinguish "account or not"

| Layer | Platform / library | Account | Ban risk | Difficulty |
|----|-----------|------|---------|------|
| **A Public content** | [yt-dlp](https://github.com/yt-dlp/yt-dlp) (YouTube + 1800 sites, actively updated daily) / [gallery-dl](https://github.com/mikf/gallery-dl) (image galleries) | No | Almost none | ✅ Use directly, most stable |
| **B Account-state** | [twscrape](https://github.com/vladkens/twscrape)(X) / [instaloader](https://github.com/instaloader/instaloader)(IG) / [TikTok-Api](https://github.com/davidteather/TikTok-Api)(TikTok) | Needs cookie / account | **High** | ⚠️ Account + proxy + pacing |

**Ask yourself first**: if you only need public videos/images → layer A, yt-dlp all the way, don't touch accounts. If you need account-state data (following/private/interactions) → layer B, be ready for account warming + heavy investment.

## The real difficulty of layer B: every account library fails on pacing

2026 evidence — X / IG / TikTok all block people at the **same point**:

- **X (twscrape)**: X simultaneously watches IP reputation / login geography / **request pacing** / cross-account patterns; any one wrong → rate limiting / shadow ban / permanent ban. Original quote: *"hitting a rate limit then immediately rotating and continuing to hammer is itself a signal"* → need **exponential backoff**, not hard rotation. twscrape has built-in rate-limit handling + optional **curl-cffi TLS impersonation** (same move as our signature layer).
- **IG (instaloader)**: single session; reuse triggers bans; users keep asking for "custom rate limiting" (issue #1922).
- **TikTok (TikTok-Api)**: runs Playwright + needs ms_token (grabbed from DevTools) + proxy + `sleep_after` and other msToken generation. **Same origin as Douyin App** (ms_token).

**Common thread = pacing decides survival**: jittered intervals + daily quota + exponential backoff + circuit breaker. This is exactly the L2/L3/L4 methodology already in Mirage's behavior layer [`interaction_policy.py`](../scripts/interaction_policy.py)—**can be abstracted into platform-agnostic pacing middleware** wrapped around these account libraries (twscrape already has it built in; instaloader lacks it most).

## TLS consistency (echoing the signature layer)

twscrape uses **curl-cffi** for TLS impersonation—exactly the same approach recommended by [`docs/tls-fingerprint.md`](tls-fingerprint.md) / [`docs/signature-layer.md`](signature-layer.md). Whether domestic Douyin or overseas X, the transport-layer JA3 answer is curl_cffi. Three deep rabbit holes (signature / App / overseas) converge here into one methodology.

## Mirage's boundaries

- Mirage hardens the web version of MediaCrawler's behavior layer; overseas platforms are a different set of libraries. **Mirage does not take over.**
- What can be borrowed is the **methodology**: layer B account libraries fear bans → use Mirage's pacing approach (jitter / quota / backoff / circuit breaker) + residential proxy + account warming.
- What Mirage can give is **signposts**: public content yt-dlp, X twscrape, IG instaloader, TikTok TikTok-Api.

## One-liner

**Overseas two layers: public content = yt-dlp all the way (zero risk); account-state X/IG/TikTok all fail on pacing (jitter + quota + exponential backoff + circuit breaker, same origin as Mirage's behavior layer) + curl_cffi fills in TLS (same origin as the signature layer). Mirage provides signposts + methodology, does not take over.**