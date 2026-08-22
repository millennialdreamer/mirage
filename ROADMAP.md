# Roadmap

What's here, what's coming, and — just as importantly — what this project will never do.

## Shipped

**Hardening**
- Five behavior layers, one command, all 7 MediaCrawler platforms (`-p all`)
- Idempotent patching with atomic write → AST validation → rollback on failure
- `--dry-run`, `--check`, `--revert`; every touched file backed up before the first write
- Regression suite runs the real regex anchors against a real MediaCrawler checkout

**Observability** *(the part other tools skip)*
- `mirage radar` — soft-ban early warning from five leading indicators, with cross-session
  baselines, per-account isolation, and an explicit refusal to guess on small samples
- `mirage canary` — offline hardening health check with meaningful exit codes
- `mirage guard-install` — git hook that warns when an upstream pull wipes your patches

**Fingerprint**
- `mirage profile` — one coherent device profile per account, with a contradiction audit
- Seeded deterministic canvas/audio noise (per-call randomness is itself a tell now)
- `--botd` / `--detect-url` — third-party verdicts instead of a score we hand ourselves
- patchright preferred over raw Playwright, to close the CDP `Runtime.Enable` leak

**Interaction**
- Human-like engine, `dry_run=True` by default, conservative quotas, minimum gaps,
  cross-session counters that survive restarts
- Circuit breaker on risk-control signals; radar-driven automatic slowdown
- Optional captcha hand-off hook (detection and humanized resume only — see below)

## Planned

| | |
|---|---|
| Platform-agnostic pacing middleware | Extract L2/L3/L4 so account-based libraries (twscrape, instaloader) can reuse the quota / backoff / circuit-breaker logic |
| Richer radar signals | Honeypot auto-detection, per-endpoint completeness baselines |
| Selector health checks | The Douyin/Kuaishou/Weibo selectors are semantic guesses; only Xiaohongshu is verified against a live page |
| Structured config | A `mirage.yaml` so quotas and thresholds stop living in constants |

## Explicitly out of scope

These aren't "not yet" — they're **no**, and here's why.

| | Why not |
|---|---|
| **Solving captchas** | A separate arms race, and a commodity one. Mirage detects and hands off to your solver; it will not defeat human verification itself. |
| **Reversing signatures** (`a_bogus`, `x-s`, `msToken`) | Lifespans measured in weeks. Bridge a maintained library instead — [docs/signature-layer.md](docs/signature-layer.md). |
| **Bundling a proxy pool** | Residential IPs you already trust usually beat a rotating pool of flagged datacenter addresses. Tooling exists in `network_resilience.py`; wiring it in is your call, not the default. |
| **Becoming an antidetect browser** | Engine-level fingerprint spoofing needs a recompiled browser. That's camoufox's job, and Mirage is not going to pretend otherwise. |
| **A distributed scheduler** | Different problem, different project. |
| **App capture built in** | Frida/Appium is a whole other stack. Mapped in [docs/app-capture.md](docs/app-capture.md), not vendored. |

## The known ceiling

The injection layer cannot fix `toString` leaks, execution-timing races, worker-realm escapes, or
property-descriptor traces. That's architecture, not effort. Expect roughly 70–80% against static
fingerprinting and 40–50% against CreepJS-style active probing.

If you need more than that, you need a different layer — and this project would rather tell you that
than sell you a number it can't back up.
