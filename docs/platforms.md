Multi-Platform Anti-Crawl Reference

Mirage's five-layer hardening (behavior layer) is universal across the **7 platforms** supported by MediaCrawler. But anti-crawl strength varies wildly from platform to platform—this table helps you choose the corresponding approach and parameter conservatism.

## Anti-Crawl Strength Tiers

| Platform | Alias | Strength | Main anti-crawl mechanisms | Are the five layers enough? | Recommendation |
|------|------|------|-------------|---------|------|
| Douyin | `dy` | 🔴 Extremely high | a_bogus / X-Bogus signature + device fingerprint ttwid + strict behavioral risk control | Behavior layer required but not sufficient | Set SLEEP to 10s+, keep volume very low, signature relies on upstream |
| Kuaishou | `ks` | 🟠 High | signature + did device identifier + risk control | Same as above | SLEEP 8s+, conservative |
| Zhihu | `zhihu` | 🟡 Medium | x-zse-96 signature + cookie validation | Behavior layer + built-in signature is enough for daily use | Default safe tier |
| Xiaohongshu | `xhs` | 🟡 Medium | x-s / x-t signature + behavioral risk control | Behavior layer + signature | Default safe tier |
| Weibo | `wb` | 🟡 Medium | cookie validation + legacy anti-crawl | Behavior layer is enough | Default safe tier |
| Bilibili | `bili` | 🟢 Medium-low | wbi signature (relatively simple) + loose risk control | Behavior layer has surplus | Can use normal tier |
| Tieba | `tieba` | 🟢 Low | basically no strong anti-crawl | Behavior layer has surplus | Can use normal / fast |

## One-Click Hardening

```bash
python apply_hardening.py <MediaCrawler根> -p all --dry-run    # 先看 7 平台会改什么
python apply_hardening.py <MediaCrawler根> -p all              # 7 平台一起加固
python apply_hardening.py <MediaCrawler根> -p dy               # 只加固抖音
python apply_hardening.py <MediaCrawler根> -p all --check      # 全平台体检
python apply_hardening.py <MediaCrawler根> -p bili --revert    # 还原某平台
```

> `cdp_browser.py` (L1) and `base_config.py` (L3) are shared across all platforms. When `-p all` is used, the first platform changes them and the rest are skipped idempotently; `core.py` (L2/L4/L5) is hardened independently per platform.

## Why “Hard to Counter”—a Two-Layer Defense

1. **Behavior layer (Mirage five layers)**: makes requests “look like a real person.” This layer is the most stable—no matter how the platform’s risk-control models change, “slower, with jitter, real Chrome, mouse movements” will always look human. **Universal across 7 platforms; change the anchor once and it adapts everywhere.**
2. **Signature layer (built into MediaCrawler)**: a_bogus / x-s / wbi, etc. This layer fails most easily—once the platform updates its signature algorithm, you have to wait for upstream MediaCrawler to catch up. **Mirage does not touch signatures; it relies on upstream** (`weekly_maintenance.sh` will remind you about upstream patches).

So “hard to counter” = a rock-solid behavior layer + a signature layer that follows upstream. Each layer does its own job, making this more resilient than any single-layer approach.

## CAPTCHA / Slider Handling

When a platform detects abnormal behavior, it may pop up a CAPTCHA or slider challenge. Mirage’s stance