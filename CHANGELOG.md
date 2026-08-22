# Changelog

> Version convention: pre-release uses `0.x.y` (semver) — each x increment = a set of mature capabilities / milestone, y = patches.

## v0.6 — Observability & Consistency (deep completion after multi-party review + red-team source read)

**Added**
- `soft_ban_radar.py` + `mirage radar`: ⭐**shadow ban early warning**. Track five leading indicators — captcha rate ↑ / response completeness ↓ / latency drift / honeypot hits / success rate decline slope — to judge "being de-weighted" **before being banned**. Cross-session baselines, multi-account isolation, and samples < 12 explicitly return "insufficient data" instead of guessing.
- `device_profile.py` + `mirage profile`: ⭐**unified device profile + self-consistency validation** (consistency > single-value spoofing) + **seeded deterministic** canvas/audio noise (constant across sessions for the same profile — per-request randomization has itself become a fake-detection signal in 2026)
- `fingerprint_benchmark.py --botd` / `--detect-url`: integrate third-party real scoring sources (FingerprintJS BotD verdict / pass rate on real detection pages + full-page screenshot)
- patchright preferred loading: patch CDP `Runtime.Enable` / `Console.enable` driver-layer leaks that injection scripts **cannot patch in principle**
- `MirageLoop(on_captcha=...)`: captcha callback hook. **Mirage does not solve captchas**, only does "detect → hook → human-like timing of backfill"

**Fixed**
- Bezier trajectory **constant speed** → smoothstep ease-in/ease-out (measured acceleration ratio 1.14 ≈ constant → 3.4 human-like accel/decel). Original docstring claimed "uniform accel → uniform decel" but code didn't implement it.
- Like/favorite validation **always True**: default checked `aria-pressed`, Xiaohongshu buttons don't have this attribute → reported "took effect" and consumed quota even when not clicked. Changed to multi-attribute snapshot + honest three-state judgment.
- Time distribution `uniform` → log-normal (measured skewness -0.01 flat-topped rectangle → +1.43 right-skewed). Injected L2/L4 templates updated accordingly; L5 fallback linear constant speed also changed to ease-in/ease-out.
- benchmark wording honesty: removed exaggerated phrases like "provable human-likeness / evidence report" (local 7 signals are self-assessed relative scores, **not evidence**)
- tests no longer hardcode personal paths (changed to env var `MIRAGE_TEST_MEDIACRAWLER` + auto-detection)

**Docs**
- `anti-detection.md` correction: previously wrote "Runtime.Enable belongs to driver-layer modification, outside scope" which was a **misjudgment** (patchright makes it a one-line dependency swap); added that stealth.min.js has been deprecated upstream and its random canvas noise principle has itself become a fingerprint signal
- Clarify the injection layer's **architectural ceiling**: four principle-level limits that cannot be bypassed — TLS/JA3, worker realm cross-checking, toString auditing, execution timing races — effective against static detection (~70-80%), capped at ~40-50% against CreepJS active cross-checking.

---

## v0.5 — Maturation / Trustworthy Release (loop-driven multi-round polish)

After multi-party independent review (using GitHub 10k★ project standards) + write/verify separation iterations, maturity from 6/10 → ~8/10 (third-party re-review: engineering 8 / hard-to-counter 8.5 / product 7.5).

**Added**
- Compliance guardrails: README first-screen usage boundary three red lines + `docs/usage-policy.md` ethical boundaries (to prevent GitHub repo removal)
- `fingerprint_benchmark.py`: before/after hardening BotScore quantitative comparison + risk level + JSON evidence report ("provable human-likeness", with honest disclaimer)
- Packaging: `pyproject.toml` (package-dir mapping scripts to the mirage package, pip installable) + unified `mirage` CLI (apply/doctor/verify/benchmark)
- `tests/test_real_anchors.py`: real MediaCrawler 7-platform original core.py anchor regression (real pytest)
- `scripts/ci.sh`: local CI (pytest + ruff + mypy + self-checks), replacing GitHub Actions
- `docs/tls-fingerprint.md`: honest boundary analysis for TLS/JA3 (CDP real Chrome page layer is naturally real)
- `docs/signature-layer.md` + `examples/douyin_signature_bridge.py`: Douyin signature four gates (a_bogus/msToken/ttwid/webid) → bridging F2 (Apache-2.0) proven template + honest maintenance reality
- `docs/app-capture.md`: app scraping 2026 real stack map (packet capture + frida to bypass pinning vs Appium UI automation; key pitfall "packet capture ≠ done, still hits signatures"; outside Mirage scope, only provides a map)
- `docs/overseas.md`: overseas platforms 2026 two-layer map (public yt-dlp / account-state X·IG·TikTok all fail on pacing) + three deep-pit convergence methodology (curl_cffi supplements TLS + pacing same-source)
- `docs/platform-coverage.md`: exhaustive full-platform coverage matrix **exhaustive edition** (all mainstream domestic and overseas: content/e-commerce/local life/music/long video/news/recruitment/WeChat/maps + overseas video/social/forums/IM/image collections/map reviews/careers; 2026 latest actively maintained stacks + honest freshness labeling + Scrapling/curl_cffi general-purpose weapons)
- `examples/bridges_quickref.py`: minimal correct bridge templates for actively maintained clean-API stacks (yt-dlp/PRAW/Telethon/instagrapi; no fake templates for older crack libraries)
- `mirage canary`: offline invalidation checkup (hardening markers/security parameters/stealth/anchor mismatch, exit-code semantics, no browser launch)
- `mirage guard-install` / `guard-uninstall`: install a git post-merge hook for MediaCrawler to warn after pulls whether hardening was overwritten by upstream (advisory mode, no silent source changes)
- core type annotations (`interaction_policy.Policy` data model) + `.github/` issue/PR templates + three deep-pit maps `docs/signature-layer.md`·`app-capture.md`·`overseas.md`
- README top "find your path by your goal" user journey navigation

**Changed / Fixed**
- Core reliability: `write()` upgraded to atomic write (tempfile+fsync+os.replace); added `write_py_safe` unified write entrypoint (atomic write + post-write AST validation + failure rollback), integrated into all three patch sites
- Runtime layer imports for three contexts (flat / deployed tools / pip package)
- Cleaned up 21 lint/type issues with ruff/mypy

---

## v0.4 — Multi-platform Support

**Added**
- Added `--platform all` to `apply_hardening.py` to harden all 7 platforms in one pass
- Supported platforms: Xiaohongshu(xhs) / Douyin(dy) / Kuaishou(ks) / Bilibili(bili) / Weibo(wb) / Tieba(tieba) / Zhihu(zhihu)
- Added `weekly_maintenance.py` (cross-platform Python replacement for the `.sh` that only worked on Mac/Linux)

**Changed**
- Generalized hardening logic: anchor detection changed from Xiaohongshu-specific APIs to platform-agnostic generic patterns

**Notes**
- Anti-crawling strength varies widely by platform (Douyin "extremely high", Tieba "low"); recommend batch testing and increasing `CRAWLER_MAX_SLEEP_SEC` for high-intensity platforms

---

## v0.3 — Human-like Interaction Engine

**Added**
- `human_interaction.py`: like / follow / favorite / comment, **default `dry_run=True`**, safety valve to avoid real clicks
- `interaction_policy.py`: daily quota caps + minimum cooldown intervals + cross-session JSON persistence + automatic daily reset
- `mirage_loop.py`: human-like main loop, automatically stops when quota is exhausted

**Notes**
- Interaction features have real external consequences (liking/following strangers), **use only alt accounts**, never touch main accounts

---

## v0.2 — Brand Upgrade

**Changed**
- Project renamed from `xhs-stealth-crawler` to **Mirage (幻影)**, alluding to "passing through detection fog without leaving traces"
- README rewritten to emphasize "for learning and research only" positioning

---

## v0.1 — Initial Release (Xiaohongshu Five-layer Hardening)

**Added**
- L1 automatic injection of `stealth.min.js` — hides automation fingerprints such as `navigator.webdriver`
- L2 random jitter sleep — eliminates the fixed rhythm machine characteristic
- L3 batch overwrite of security parameters in `base_config.py` (single concurrency / disable headless / preserve login state)
- L4 startup warm-up — stay on the page for a few seconds before searching, like a real person viewing the page
- L5 Bezier mouse + scroll simulation (`human_behavior.py`)
- `apply_hardening.py`: one-click patching, idempotent (second run makes zero changes) + automatic backup + `--revert` full restore