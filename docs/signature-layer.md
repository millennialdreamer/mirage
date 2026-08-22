# Signature Layer: Douyin's Four Gates and the Correct Solution of "Bridging Existing Libraries"

> Bottom line upfront: Douyin's signature anti-crawling is **four gates stacked**. Reverse-engineering from scratch is a bottomless pit recognized industry-wide by 2026
> (industry phrase: *"Most TikTok Scrapers on GitHub Are Dead"*). The correct solution is not building the signature yourself, but
> **bridging to the actively maintained existing library [F2](https://github.com/Johnserf-Seed/f2) (Apache-2.0)**—it has already solved all four gates.
> Mirage's role is **to provide a correct bridging template + `mirage canary` monitoring for failure**, not to take over, not to reverse-engineer itself, not to guarantee upstream compatibility
> (this is MediaCrawler's request layer, not Mirage's behavior layer).

## Where Exactly Douyin Blocks You (Four Gates, End-to-End Testing)

| Gate | Symptom | Layer |
|------|---------|-------|
| ① Cannot get id | Homepage is a pure SSR empty shell; even video/user id cannot be extracted, you have to bypass via search/share/homepage links | Request layer |
| ② msToken | **Not in cookie, generated dynamically** (another anti-crawler) | Request layer |
| ③ a_bogus + ttwid | Requests require correct a_bogus signature + ttwid | Request layer |
| ④ webid / verifyFp / parameters | Also need a bunch of parameters like webid, verifyFp, s_v_web_id, plus frequent Douyin changes | Request layer |
| ⑤ JA3 transport fingerprint | httpx exposes TLS fingerprint as Python when sending signed requests | Request layer (see [tls-fingerprint.md](tls-fingerprint.md)) |

**a_bogus is only the first gate; there are four more behind it.** Cracking a_bogus alone is completely insufficient—this is exactly why many scrapers that "only did xbogus/abogus" died collectively in 2026.

## The Right Solution: Bridging F2 (Each Gate Has a Corresponding Real Solution)

F2 (Johnserf-Seed/f2, **Apache-2.0**, actively maintained, covers Douyin/TikTok/Weibo) has managers that correspond one-to-one with the four gates:

| Gate | F2 Actual API |
|------|---------------|
| ① id | `SecUserIdFetcher.get_sec_user_id(share/homepage URL)` — reverse-resolve sec_user_id from the link, bypassing the SSR empty shell |
| ② msToken | `TokenManager.gen_real_msToken()` (gets a real token over network) / `gen_false_msToken()` (pure local fallback) |
| ③ a_bogus | `ABogusManager.model_2_endpoint(ua, base_endpoint, params)` → returns a complete URL with a_bogus filled in |
| ③ ttwid | `TokenManager.gen_ttwid()` |
| ④ webid / verifyFp | `TokenManager.gen_webid()` / `VerifyFpManager.gen_verify_fp()` / `gen_s_v_web_id()` |
| ⑤ JA3 | `curl_cffi.requests.get(url, impersonate="chrome")` (see [tls-fingerprint.md](tls-fingerprint.md)) |

A runnable bridging reference template is at [`examples/douyin_signature_bridge.py`](../examples/douyin_signature_bridge.py) (written against F2's current actual API).

## Why "Bridge" Instead of "Mirage Doing It Itself"

1. **Reverse-engineering from scratch = bottomless pit**: Douyin's a_bogus/msToken uses ollvm obfuscation + VMP + frequent changes; reverse-engineered results often have a lifespan of less than several weeks, and a solo maintainer can't keep up.
2. **F2 is already keeping up**: dedicated maintenance + community + updates with Douyin changes—stand on its shoulders, don't reinvent the wheel.
3. **Belongs to request layer, not behavior layer**: What Mirage hardens is "human-likeness" (behavior layer); the signature is MediaCrawler's request layer. If Mirage takes it over, it becomes tightly coupled with upstream and breaks when upstream changes. So Mirage **only provides a bridging template + uses `mirage canary` to monitor whether anchors/hardening are mismatched**, not taking over.

## Maintenance Reality (Honest, No Guarantees)

- This layer **will** fail as Douyin changes—this is the nature of signature anti-crawling, not a bug.
- Survival strategy: **rely on F2 upstream + `mirage canary` periodic offline health checks + wait for F2 to catch up when it fails** (or switch to [Evil0ctal's API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API)).
- Douyin's anti-crawling intensity is **the highest** among all platforms; only use burner accounts, low frequency, and always be ready for failure. Never promise "permanently available".

## Comparison with Xiaohongshu (Much Easier Signature Layer)

Xiaohongshu's `x-s` / `x-s-common` signatures are **much more manageable** than Douyin's: ready-made libraries [`Spider_XHS`](https://github.com/cv-cat/Spider_XHS) / [`xhshow`](https://github.com/Cloxl/xhshow) work directly, with maintenance costs far lower than Douyin. Again, it's "bridging existing libraries" rather than reverse-engineering yourself.

## In One Sentence

**Douyin's signature four gates are fatal to reverse-engineer from scratch; the correct solution is bridging F2 (Apache-2.0, already solves all four gates) + curl_cffi for JA3, with Mirage providing the correct template + canary monitoring, not taking over, not building its own.**