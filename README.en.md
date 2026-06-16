# Mirage · Xiaohongshu (XHS) Crawler Anti-Detection Hardening

<sub>**Mirage** — making risk control see nothing but a realistic human illusion.</sub>

> One-click **five-layer anti-detection hardening** for [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler),
> making Xiaohongshu (XHS) automated scraping as **undetectable as possible** — no warnings, no throttling, no bans.

**It is not another crawler.** It's a hardening toolkit + security methodology: on an already-working MediaCrawler installation, run one command and it transforms from "naked bot" into "almost human-like". All changes are **auto-backed up, idempotent, and fully revertible** — never damage your files.

**Two core capabilities:** ① **Five-layer scraping hardening** (below); ② A **human-like interaction engine** for safe likes/follows/saves/comments (see "Interaction Engine" section below).

```bash
python scripts/apply_hardening.py /path/to/MediaCrawler --dry-run   # Preview changes first
python scripts/apply_hardening.py /path/to/MediaCrawler             # Apply (auto-backup)
python scripts/apply_hardening.py /path/to/MediaCrawler --check     # Verify all five layers
```

## ✨ Five-Layer Protection

| Layer | Blocks | How it works |
|-------|--------|--------------|
| **L1** stealth.min.js injection | `navigator.webdriver` and other automation fingerprints | Injected via CDP when browser starts |
| **L2** Randomized jitter sleep | Fixed intervals = machine rhythm | `base × U(0.7,1.6)`, 6s → actual 4.2~9.6s random |
| **L3** Batch limit + safe parameters | High exposure per round, headless browser | ≤8 items per batch, real Chrome, single concurrency, headless disabled |
| **L4** Startup warm-up | Immediate search = non-human | Stay 3~8s before first search |
| **L5** Mouse + scroll simulation | Page "freezes" during sleep | Random scroll between page turns + random mouse movements |

> Layer-by-layer explanation: [docs/anti-detection.md](docs/anti-detection.md)

> 🌐 **Not just Xiaohongshu**: The five-layer hardening works for all **7 platforms** in MediaCrawler (Xiaohongshu / Douyin / Kuaishou / Bilibili / Weibo / Tieba / Zhihu). Apply to all with `-p all`. Anti-scraping strength levels and recommended parameters per platform: [docs/platforms.md](docs/platforms.md)

## 📦 Prerequisites

- **Python 3.11+** (same as MediaCrawler)
- A working [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) installation
- Playwright + Chromium (only needed for `verify_stealth.py` self-check): `pip install playwright && playwright install chromium`
- **Core script `apply_hardening.py` has zero extra dependencies** — uses only Python standard library, run directly after cloning

## 🚀 Quick Start

Prerequisite: you have MediaCrawler installed and working.

```bash
git clone https://github.com/millennialdreamer/mirage.git
cd mirage

# 1. Dry-run first to see which files will be changed (no disk writes)
python scripts/apply_hardening.py ~/path/to/MediaCrawler --dry-run

# 2. Apply when ready (each modified file is backed up as *.xhs-stealth.bak)
python scripts/apply_hardening.py ~/path/to/MediaCrawler

# 3. Verify: confirm all five layers are in place
python scripts/apply_hardening.py ~/path/to/MediaCrawler --check

# Revert anytime
python scripts/apply_hardening.py ~/path/to/MediaCrawler --revert
```

## 🧰 Scripts Overview

| Script | Purpose |
|--------|---------|
| `scripts/apply_hardening.py` | ⭐ Core: one-click five-layer hardening, idempotent / auto-backup / revertable / dry-run / verify |
| `scripts/safe_profile.py` | One-click switch between safe / normal / aggressive profiles, with estimated scrape rate |
| `scripts/verify_stealth.py` | Fingerprint self-test: open browser and compare "before/after injection", confirm webdriver etc. are hidden |
| `scripts/human_behavior.py` | Human behavior simulation module (jitter sleep / warm-up / mouse scroll), reusable for manual integration |
| `scripts/weekly_maintenance.sh` | Weekly update of stealth.min.js + check for upstream anti-detection patches |
| `scripts/human_interaction.py` | ⭐ Interaction engine: identify + human-like click for likes/follows/saves/comments (dry-run by default) |
| `scripts/interaction_policy.py` | Interaction quotas: conservative daily caps + min intervals + cross-session persistent counters |
| `scripts/mirage_loop.py` | ⭐ Ultimate "human-like account farming" main loop: heavy browsing + light restrained interaction + risk control circuit breaker |

## 🤝 Interaction Engine (Likes / Follows / Saves / Comments)

Beyond scraping hardening, Mirage provides a **human-like interaction engine** — safely like, follow, save, comment just like a real person. **Zero bans come from restraint + realism, not mass actions**:

- **dry-run on by default**: moves mouse into position, demonstrates, but doesn't actually click. Only switch `dry_run=False` once confident.
- **Conservative daily caps + min intervals + cross-session counters**: prevents instant-likes, overwhelming volumes, or reboot-bypass.
- **Bézier clicks + view-then-like + two-stage decision**: even after viewing, only ~45% actually interact, reserving quota for quality content.
- **Ultimate "human-like farming" loop**: heavy browsing + light restrained interaction + auto circuit-breaker on detection (CAPTCHA/throttling).

```python
from mirage_loop import MirageLoop
loop = MirageLoop(page, dry_run=True, conservative=True)   # Recommended for new accounts
await loop.run()
```

⚠️ Interactions have **real external consequences** (actually liking/commenting on real people) — **use only on test accounts**. Full safety guide: [docs/interaction-safety.md](docs/interaction-safety.md)

## 🛡️ Safe Usage (Read First)

Hardening reduces probability, **it is not a safety license**. Three golden rules:

1. **Use only test accounts; never touch your main account with crawlers.**
2. **Scale up gradually**: Day 1 ≤30 items, Day 2 ≤100 items, rest hours in between, never scrape continuously.
3. Default to **safe profile**; `fast` profile significantly increases detection risk — use only when you're willing to "go all-out for a quick grab".

Full guide (including what to do if flagged): [docs/safe-usage.md](docs/safe-usage.md)

## 🔬 Why It Works

Xiaohongshu's risk control fundamentally judges "how human-like you are". This tool does not crack signatures — instead it makes automation as human-like as possible at the **behavioral layer**: real Chrome, random rhythm, human pauses, mouse activity. Behavioral layer is more stable than signing layer — signing algorithms change every few weeks, but "slower, jittery, mouse-moving" will always resemble human behavior. Details: [docs/anti-detection.md](docs/anti-detection.md)

## ⚠️ Known Limitations / Not Supported

Mirage is a behavioral-layer hardening tool for **MediaCrawler web-based crawlers**. The following scenarios are **beyond its scope** — please do not misuse it:

1. **App scraping (client-side)**: Mirage only hardens Playwright-driven **web scraping**. Mobile apps, desktop clients for data extraction require different stacks (packet capture via Charles/mitmproxy, hooking via Frida, emulators, etc.) — Mirage cannot help here.

2. **International platforms**: TikTok, Instagram, X (Twitter), YouTube, etc. use **different crawler frameworks** not supported by MediaCrawler — hence not covered by Mirage.

3. **Signature algorithm reverse-engineering**: Signatures like Douyin `a_bogus`, Xiaohongshu `x-s`, Kuaishou signatures are maintained upstream by MediaCrawler. When platforms update their signature algorithms, scraping may **temporarily break** — wait for upstream fixes. Mirage does not participate in signature reversal; `weekly_maintenance.sh` reminds you to check upstream updates.

4. **Extreme network environments**: Weak network, reconnection, unstable proxies require a dedicated `network_resilience` module for retry and recovery. Mirage core assumes basic network connectivity and does not include disconnection resilience.

> In short: Mirage does one thing well — **make MediaCrawler's web automation behave more like a human**. For needs beyond that, use dedicated tools.

## ⚠️ Disclaimer

For learning and research only. **Hardening reduces the probability of detection but cannot eliminate it** — any crawler may be flagged. Users must comply with Xiaohongshu's Terms of Service and robots rules, exercise reasonable frequency control, and not use it for commercial or any inappropriate purposes. All consequences arising from the use of this tool are the sole responsibility of the user.

## 📄 License

This project is released for learning and research purposes, inheriting the non-commercial spirit of upstream MediaCrawler. See [LICENSE](LICENSE).
