# Safe Usage Guide

This guide is for you if you want to scrape some Xiaohongshu data and are worried about your account being flagged. Remember one thing: **crawling is always risky; hardening only lowers the probability, it is not a get-out-of-jail-free card.** Follow the rules below.

## Rule number one: only use an alt account, never let your main account touch the crawler

For any crawler operation, absolutely never use the main account you use daily for posting notes, chatting, and shopping. No matter how human-like the crawler's behavior is, there will always be gaps. Once the main account is flagged by risk control, followers, notes, and the bound phone number may all suffer.

**Correct approach**: Register a brand-new alt account with no connection to your main account, dedicated to running the crawler. It doesn't matter if it has no followers or notes; if it gets killed you won't feel bad. Changing IP or device won't save your main account — platforms judge based on a combination of account, device fingerprint, and behavior patterns.

## Scale up gradually; don't hammer it from the start

Xiaohongshu's rate limiting is **cumulative**, not one-shot. Increase request volume slowly, like a beginner at the gym:

- **Day one**: **no more than 30 items** total. The goal is to verify the pipeline works, not to test the limit.
- **Day two**: **no more than 100 items**. While at it, observe the alt account's status — can it post notes normally? are comments collapsed?
- **Day three onwards**: you can increase further, but **never hammer continuously**. Crawl a batch, stop for a few hours, then crawl the next batch.

A real person won't continuously browse other people's profiles for hours. "Slow + intermittent" is what looks human.

## Three rate tiers: always use safe by default

The tool has three built-in tiers, switchable with a single command. **Always use `safe` normally, unless you really don't care whether this account lives or dies.**

| Tier | Batch size | Base interval | When to use |
|------|---------|---------|--------|
| **safe** | ≤8 items | 6s (actual jitter 4.2–9.6s) | **Default**, for stability |
| normal | 15 items | 3s (jitter 2.1–4.8s) | Time-crunched, risk is on you |
| fast | 30 items | 1s + 3 concurrent | **Dangerous**, only when you're "going all in" |

Switch tier commands (under the MediaCrawler directory):

```bash
python config/safe_profile.py            # show current tier + estimated rate
python config/safe_profile.py safe       # switch to the safe tier
python config/safe_profile.py normal     # switch to the normal tier
```

> Note: don't run multiple crawler windows at the same time — the rates add up, which is equivalent to secretly switching to fast.

## Hardening is not a silver bullet; be mentally prepared

The five layers of hardening can make your requests "more human-like", but **no tool can guarantee 100% detection avoidance**. Xiaohongshu's risk control upgrades every few weeks. If you crawl too hard, or stare at a single user for too long, it will still get suspicious. Hardening is a shield, but if the request volume "machete" is too heavy, the shield won't hold.

## What to do if you get warned? Stop immediately

If the alt account receives "abnormal operation" or "behavior restricted" warnings, or the crawled data suddenly comes back empty/garbled — **stop all crawlers immediately, and don't run them again that day**. Then:

1. **Stop and rest**; close all crawler windows.
2. **Switch to safe tier**, and reduce the batch size further: edit `config/base_config.py` and change `CRAWLER_MAX_NOTES_COUNT` to **≤3**. Fewer is safer.
3. **Make sure you're using an alt account**. If you slipped and used your main account, stop immediately and never run on your main account again.
4. **Check whether hardening is still in place**: run `python apply_hardening.py <your-MediaCrawler-path> --check` to confirm the five layers haven't been overwritten.

If the alt account returns to normal the next day, it was only a mild warning. If it gets caught repeatedly, the account may have been permanently flagged — switch to a new alt account.

## Upstream updates will wipe out the hardening

This tool patches `MediaCrawler`. If you `git pull` updates to MediaCrawler, **your hardening will be overwritten**. The correct order:

1. Revert before updating: `python apply_hardening.py <path> --revert`
2. Then `git pull`
3. After pulling, re-apply the patch: `python apply_hardening.py <path>`
4. Run a health check to confirm: `python apply_hardening.py <path> --check`

If that's too much trouble, at least run `--check` after each pull to confirm the five layers are still in place.

## Using real Chrome + reusing a logged-in account is safest

This tool enables CDP mode by default (`ENABLE_CDP_MODE=True` + `CDP_CONNECT_EXISTING=True`): it directly takes over your already-open, already-logged-in real Chrome with the alt account, instead of launching a fully automated browser from scratch each time.

Why this is safer:

- The fingerprint of real Chrome (resolution, fonts, GPU) is identical to a normal user's, so it won't be treated as an "automation tool".
- Reusing a logged-in session avoids captchas and slider verifications on each login — those verification steps are themselves risk-control observation points.

How to do it: first log in to your alt account manually in Chrome, keep the window open, then start the crawler — it will take over automatically.

---

**One last thing**: Xiaohongshu is not yours to crawl freely, and getting caught is normal. This tool is only suitable for doing some technical practice and small-scale data experiments with an alt account. Don't use it for commercial collection or large-scale scraping — that is a legal risk far more serious than a ban. Protect yourself.