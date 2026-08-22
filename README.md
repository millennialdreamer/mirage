<h1 align="center">Mirage</h1>

<p align="center">
  <strong>Know you're being throttled — before you're banned.</strong>
</p>

<p align="center">
  Behavior-layer hardening for <a href="https://github.com/NanmiCoder/MediaCrawler">MediaCrawler</a>,
  plus the early-warning radar that every other anti-detect tool forgets to ship.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-blue">
  <img alt="Dependencies" src="https://img.shields.io/badge/core%20deps-zero-brightgreen">
  <img alt="Platforms" src="https://img.shields.io/badge/platforms-7-orange">
  <img alt="Tests" src="https://img.shields.io/badge/tests-24%20passing-success">
  <img alt="License" src="https://img.shields.io/badge/license-research--only-lightgrey">
</p>

---

Most anti-detect tooling helps you **look** human. None of it tells you **when that stopped working**.

Platforms rarely ban you outright. First they quietly degrade you: a few more captchas, responses that
still return `200` but come back thinner, latency creeping up, success rate sliding. By the time you
see a hard `403`, you've been burning proxy budget on garbage data for days.

Mirage does both halves:

1. **Hardening** — one command patches your existing MediaCrawler install with five behavior layers.
2. **Observability** — a soft-ban radar that reads five leading indicators and tells you to slow down
   *before* the ban lands.

> **Why Mirage can do #2 when nobody else can:** an anti-detect browser only sees fingerprints. A proxy
> vendor only sees IPs. A captcha service only sees challenges. Mirage sits at the one place where
> *what you inject*, *what you send*, and *what comes back* are all visible at once.

## Quick start

```bash
git clone https://github.com/millennialdreamer/mirage.git && cd mirage

# 1. See exactly what would change — nothing is written
python scripts/apply_hardening.py /path/to/MediaCrawler --dry-run

# 2. Apply it (every touched file is backed up first)
python scripts/apply_hardening.py /path/to/MediaCrawler

# 3. Health-check all five layers
python scripts/apply_hardening.py /path/to/MediaCrawler --check
```

Changed your mind? `--revert` restores every file from backup. Ran it twice? It's idempotent — zero diff.

Core hardening has **zero third-party dependencies**. Clone it and it runs.

## The radar — Mirage's actual differentiator

```console
$ mirage radar

⚠ Soft-ban radar · account "worker-03"
  Level: WARNING     Risk: 47/100     Samples: 61
  Signals:
    captcha rate:        0.15
    completeness drop:   0.22      ← responses are quietly getting thinner
    latency ratio:       1.9x
    success rate:        0.71
    honeypot hits:       0
  Advice: Clear degradation trend. Halve your rate now, shrink batches,
          pause interactions, and watch whether it recovers.
```

| Signal | Why it leads the ban |
|---|---|
| Captcha rate ↑ | Should sit at ~0. Anything above means you're already suspected |
| **Response completeness ↓** | **The classic shadow-ban tell — still `200`, just quietly thinner** |
| Latency drift | Throttling shows up as median response time creeping up |
| Honeypot hits | Conclusive. Invisible elements are only ever touched by automation |
| Success-rate slope | Chronic degradation, measured against your own baseline |

Baselines persist across sessions and are isolated per account. Under 12 samples it refuses to
guess and says so — a trend built on 5 data points is noise, not signal.

## Where Mirage fits

It does **not** compete with browser-level stealth. It sits on top of it and covers what that layer can't.

| | Mirage | undetected-chromedriver / patchright | camoufox / antidetect browsers |
|---|:--:|:--:|:--:|
| Operating layer | behavior + ops | browser driver | browser engine |
| Patches your **existing** crawler | ✅ | ❌ | ❌ |
| CDP `Runtime.Enable` leak | ✅ *(via patchright)* | ✅ | ✅ |
| Canvas / WebGL spoofing | ⚠️ injection-level | ❌ | ✅ engine-level |
| Pacing, quotas, circuit-breaking | ✅ | ❌ | ❌ |
| **Soft-ban early warning** | ✅ | ❌ | ❌ |
| Fingerprint self-consistency audit | ✅ | ❌ | ⚠️ |

**Use them together.** Mirage will actively tell you to install `patchright` — it fixes a driver-layer
leak that no injected script can reach.

## Features

<details open>
<summary><strong>Five hardening layers</strong> — one command, all 7 MediaCrawler platforms</summary>

| Layer | Signal it removes | How |
|---|---|---|
| **L1** stealth injection | `navigator.webdriver` and friends | auto-injected at CDP launch |
| **L2** jittered sleep | fixed intervals = machine cadence | log-normal, right-skewed like real humans |
| **L3** batch + safe params | high burst exposure, headless | ≤8 items, real Chrome, single concurrency |
| **L4** warm-up | opening straight into a search | 3–8s dwell before first query |
| **L5** mouse + scroll | a frozen page during sleep | Bézier curves with ease-in-out |

`-p all` covers Xiaohongshu, Douyin, Kuaishou, Bilibili, Weibo, Tieba and Zhihu.
</details>

<details>
<summary><strong>Device profile</strong> — consistency beats single-value spoofing</summary>

Modern detectors don't check values, they check for **contradictions**: a Windows UA with an Apple GPU,
a Shanghai timezone with US-only locales, 16 cores on the main thread and 4 in a worker.

Spoofing one field at a time makes you *more* detectable, not less. Mirage derives every injected value
from one coherent profile and audits it before use:

```bash
mirage profile worker-03 --emit fp.js
# [device profile seed=worker-03] ✓ self-consistent
#   Windows 11 / Win32 / 12 cores 8GB / 1920x1080 / zh-CN / Asia/Shanghai
#   GPU=ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11...)
```

Same seed always yields the same profile, so a given account stays stable across sessions.
Canvas and audio noise is **seeded and deterministic** — per-call randomness is itself a tell now,
since detectors simply render twice and compare hashes.
</details>

<details>
<summary><strong>Ops tooling</strong> — canary, upstream guard, captcha hook</summary>

- `mirage canary <path>` — offline health check. Are the patches still there? Did an upstream refactor
  break the anchors? Exit code included, so CI can gate on it. Makes zero network calls.
- `mirage guard-install <path>` — git hook that warns you when an upstream `pull` silently wipes your
  hardening. It only warns; it will never rewrite third-party source behind your back.
- `MirageLoop(on_captcha=...)` — **Mirage does not solve captchas.** It detects, hands off to your own
  solver, and humanizes the resume timing. Resuming instantly after a solve is itself a robot tell.
</details>

<details>
<summary><strong>Verification</strong> — third-party judgment, not self-scored</summary>

```bash
python scripts/fingerprint_benchmark.py --botd        # FingerprintJS BotD verdict
python scripts/fingerprint_benchmark.py --detect-url  # real detection page + full screenshot
```

The local 7-signal BotScore is a **relative baseline, not evidence** — it's a score we give ourselves.
Ranked by how much you should trust them: third-party verdict > real detection page > local score.
</details>

## Honest limits

Read this before you rely on it. Every claim below is a limit of the *architecture*, not of the effort.

- **Injection layer has a hard ceiling.** `toString` leaks, execution-timing races, worker-realm escapes
  and property-descriptor traces cannot be fixed from injected JavaScript. Expect it to hold against
  static fingerprinting (~70–80%) and to fall well short against CreepJS-style active probing (~40–50%).
  Going beyond that requires a recompiled engine — out of scope here, by design.
- **TLS/JA3 is not ours.** It's decided by the network stack; JS can't touch it. See
  [docs/tls-fingerprint.md](docs/tls-fingerprint.md).
- **`stealth.min.js` is deprecated upstream** (Feb 2025), and its random-canvas-noise approach has since
  become a detection signal in its own right. Install `patchright`; `mirage doctor` will nag you about it.
- **Signature layers (`a_bogus`, `x-s`, `msToken`) are not ours either.** We point you at maintained
  libraries instead of pretending to reverse them — [docs/signature-layer.md](docs/signature-layer.md).
- **Hardening lowers probability. It does not eliminate risk.** Anything automated can still get caught.

## Documentation

| Topic | |
|---|---|
| How the five layers work | [docs/anti-detection.md](docs/anti-detection.md) |
| Safe usage, and what to do after a warning | [docs/safe-usage.md](docs/safe-usage.md) |
| Per-platform anti-crawl strength | [docs/platforms.md](docs/platforms.md) |
| Douyin's four signature walls → bridging F2 | [docs/signature-layer.md](docs/signature-layer.md) |
| TLS / JA3 boundaries | [docs/tls-fingerprint.md](docs/tls-fingerprint.md) |
| App capture: mitmproxy vs Appium | [docs/app-capture.md](docs/app-capture.md) |
| Overseas platforms | [docs/overseas.md](docs/overseas.md) |
| Full platform coverage matrix | [docs/platform-coverage.md](docs/platform-coverage.md) |
| Interaction safety | [docs/interaction-safety.md](docs/interaction-safety.md) |
| Usage policy and ethics | [docs/usage-policy.md](docs/usage-policy.md) |

## CLI

| Command | |
|---|---|
| `mirage apply <path> [-p platform] [--dry-run/--check/--revert]` | apply / inspect / undo hardening |
| `mirage radar [--account X] [--reset]` | soft-ban early warning |
| `mirage profile <seed> [--emit file]` | generate + audit a device profile |
| `mirage canary <path>` | offline hardening health check |
| `mirage guard-install / guard-uninstall <path>` | git hook against upstream overwrites |
| `mirage doctor` | environment check |
| `mirage verify` / `mirage benchmark` | fingerprint checks *(you run these yourself)* |

## Install

```bash
pip install -e .                    # core, zero third-party deps
pip install -e ".[browser]"         # + patchright, for fingerprint verification
```

Python 3.9+. You need a working [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) install —
Mirage hardens it, it isn't a crawler itself.

## Development

```bash
bash scripts/ci.sh                              # pytest + ruff + mypy
git config core.hooksPath .githooks             # run CI automatically before every push
```

Patches to third-party source go through atomic write → AST validation → rollback on failure. The
regression suite runs the real regex anchors against a real MediaCrawler checkout (auto-detected, or
set `MIRAGE_TEST_MEDIACRAWLER`); it skips cleanly when there isn't one. No third-party source is
vendored into this repo.

## Scope and responsibility

For **learning, research and personal testing**. Use throwaway accounts. Keep the rate low.

To be blunt about it: most platforms' terms of service already prohibit automated access and automated
interaction. This project won't pretend that following a checklist makes that go away. **Whether to use
it, what to use it on, and the consequences are yours to judge and yours to carry.** It ships technique
and boundaries — not an endorsement of any particular use.

Interaction engine defaults to `dry_run=True`, stops on captcha rather than attempting to defeat it, and
enforces daily quotas below what a heavy human user would hit. See
[docs/usage-policy.md](docs/usage-policy.md).

## License

Research and non-commercial use — see [LICENSE](LICENSE).
