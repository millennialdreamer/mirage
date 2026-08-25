# -*- coding: utf-8 -*-
"""
soft_ban_radar.py — early-warning radar for shadow bans (Mirage's "observation post" capability).

## Why it is needed

The existing `mirage_loop._danger()` only trips the circuit breaker **after a CAPTCHA appears** — by then the account is already
flagged; it is "after the fact".
But platforms usually **quietly de-rank** (shadow ban) before a hard ban: the account still works, but CAPTCHAs become more
frequent, returned content shrinks,
responses slow down, and success rate gradually drops. Individually none of these signals look abnormal; only the trend reveals them.

That is what the radar does: **detect that you are "being watched" before the ban**, and proactively slow down / switch accounts
instead of waiting for a 403.

## Why Mirage does this (and not someone else)

Anti-detection browsers only handle fingerprints, proxy providers only handle IPs, CAPTCHA solvers only handle passing CAPTCHAs —
**only Mirage sits at the intersection of
"what was injected + what was sent + what came back"**, the only position in the whole chain that can observe these five signals.

## Five early-warning signals

| Signal | Meaning | Why it is a precursor |
|--------|---------|----------------------|
| CAPTCHA trigger rate ↑ | Share of CAPTCHA/slider challenges in the recent window | Normally should be ≈0; once non-zero, you are
already suspected |
| Return completeness ↓ | Fields obtained / fields expected | **The most typical de-ranking symptom: it returns but returns less**
(silently dirtied) |
| Latency distribution drift | Recent median latency / baseline median latency | Responses become noticeably slower when rate-limited |
| Honeypot hit | Caught/clicked a hidden element | **Hard evidence** — elements invisible to humans are only touched by bots |
| Success rate decline slope | Baseline success rate − recent success rate | Direct manifestation of chronic deterioration |

## Honest boundaries (important)

- This is a **heuristic trend judgment, not an exact verdict**. It suggests "should you slow down", not "you are banned".
- With insufficient samples (< `MIN_SAMPLES`) it **explicitly returns "insufficient data" instead of guessing** — trends from tiny
samples are meaningless.
- Thresholds are empirical values and vary widely across platforms; tune them with `SoftBanRadar(thresholds=...)`.
- It **cannot replace** risk-control circuit breaking (`_danger()`); the two are the relationship of "early warning" and "emergency
braking", both are needed.

## Usage

    from soft_ban_radar import SoftBanRadar

    radar = SoftBanRadar()                       # auto-load historical baseline
    ...record an observation after each request/interaction...
    radar.observe(ok=True, latency=1.3, completeness=0.95, captcha=False)

    v = radar.assess()
    if v.level in ("warning", "danger"):
        print(v.advice)                          # slow down or stop as advised
"""
from __future__ import annotations

import json
import os
import statistics
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

# Window and sample size
RECENT_WINDOW = 20        # how many observations count as "recent"
BASELINE_WINDOW = 60      # max baseline lookback (older discarded to avoid stale data dragging)
MIN_SAMPLES = 12          # below this sample count no conclusion — tiny-sample trends are meaningless
MIN_BASELINE = 8          # baseline needs at least this many to be comparable

# Judgment thresholds (empirical values, vary widely by platform, can be overridden via constructor args)
DEFAULT_THRESHOLDS = {
    "captcha_rate_warn": 0.01,     # any CAPTCHA in the recent window should raise alert
    "captcha_rate_alert": 0.10,
    "completeness_drop_warn": 0.10,   # completeness drops 10% vs baseline
    "completeness_drop_alert": 0.25,
    "latency_ratio_warn": 1.6,        # median latency rises to 1.6x baseline
    "latency_ratio_alert": 2.5,
    "success_drop_warn": 0.15,        # success rate drops 15 percentage points vs baseline
    "success_drop_alert": 0.30,
}

# Per-signal weights (honeypot is hard evidence, separately given the highest severity)
WEIGHTS = {"captcha": 26, "completeness": 24, "latency": 16, "success": 22, "honeypot": 12}


@dataclass
class Observation:
    """One observation. If latency/completeness are unavailable, pass None and the radar will skip the corresponding signal."""
    ts: float
    ok: bool = True
    latency: Optional[float] = None        # seconds
    completeness: Optional[float] = None   # 0~1: obtained fields / expected fields
    captcha: bool = False
    honeypot: bool = False


@dataclass
class Verdict:
    level: str                              # insufficient data / normal / watch / warning / danger
    score: int                              # 0~100, higher means more dangerous
    advice: str
    signals: dict = field(default_factory=dict)
    samples: int = 0

    def should_slow_down(self) -> bool:
        return self.level in ("watch", "warning", "danger")

    def should_stop(self) -> bool:
        return self.level == "danger"


def _median(xs):
    vals = [x for x in xs if x is not None]
    return statistics.median(vals) if vals else None


def _grade(value, warn, alert):
    """Map a metric to a 0~1 severity (below warn=0, at alert=1, linear in between)."""
    if value is None or value <= warn:
        return 0.0
    if value >= alert:
        return 1.0
    span = alert - warn
    return (value - warn) / span if span > 0 else 1.0


class SoftBanRadar:
    """Shadow-ban early warning: accumulate observations → compare baseline → produce risk level and advice."""

    def __init__(self, state_path: str = "~/.mirage/softban_radar.json",
                 thresholds: Optional[dict] = None, account: str = "default") -> None:
        self.path = os.path.expanduser(state_path)
        self.account = account                      # separate baseline per account, no cross-contamination
        self.th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._obs: list[Observation] = []
        self._load()

    # ── Persistence: trend judgment depends on historical baseline, must span sessions ──────────────
    def _load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get(self.account, [])
            self._obs = [Observation(**o) for o in raw][-BASELINE_WINDOW:]
        except Exception:
            self._obs = []                          # missing/corrupt → start from zero

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            data = {}
            if os.path.isfile(self.path):
                try:
                    with open(self.path, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data[self.account] = [asdict(o) for o in self._obs[-BASELINE_WINDOW:]]
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, self.path)              # atomic write
        except Exception:
            pass                                    # a save failure must never interrupt the main flow

    # ── Observation ────────────────────────────────────────────────
    def observe(self, ok: bool = True, latency: Optional[float] = None,
                completeness: Optional[float] = None, captcha: bool = False,
                honeypot: bool = False) -> None:
        """Record one observation. Call after each request / each interaction round."""
        self._obs.append(Observation(ts=time.time(), ok=ok, latency=latency,
                                     completeness=completeness, captcha=captcha,
                                     honeypot=honeypot))
        self._obs = self._obs[-BASELINE_WINDOW:]
        self._save()

    # ── Judgment ────────────────────────────────────────────────
    def assess(self) -> Verdict:
        """Compare the "recent window" against the "earlier baseline", output risk level + advice."""
        n = len(self._obs)
        if n < MIN_SAMPLES:
            return Verdict(level="insufficient data", score=0, samples=n,
                           advice=f"Only {n} observation(s) (need >= {MIN_SAMPLES}). Too few to mean anything — "
                                  f"keep going normally and do not draw conclusions from this.")

        recent = self._obs[-RECENT_WINDOW:]
        baseline = self._obs[:-RECENT_WINDOW] or self._obs[:max(1, n // 2)]

        sig: dict = {}
        sev: dict = {}

        # 1) CAPTCHA trigger rate (normally should be ≈0)
        cap_rate = sum(1 for o in recent if o.captcha) / len(recent)
        sig["captcha rate"] = round(cap_rate, 3)
        sev["captcha"] = _grade(cap_rate, self.th["captcha_rate_warn"], self.th["captcha_rate_alert"])

        # 2) honeypot hit (hard evidence, one hit is full severity)
        hp = sum(1 for o in recent if o.honeypot)
        sig["honeypot hits"] = hp
        sev["honeypot"] = 1.0 if hp else 0.0

        can_compare = len(baseline) >= MIN_BASELINE

        # 3) return completeness drop (de-ranking's most typical symptom: returns but shrinks)
        r_comp, b_comp = _median([o.completeness for o in recent]), _median([o.completeness for o in baseline])
        if can_compare and r_comp is not None and b_comp is not None:
            drop = b_comp - r_comp
            sig["completeness drop"] = round(drop, 3)
            sev["completeness"] = _grade(drop, self.th["completeness_drop_warn"], self.th["completeness_drop_alert"])
        else:
            sev["completeness"] = 0.0

        # 4) latency drift (rate limiting makes responses noticeably slower)
        r_lat, b_lat = _median([o.latency for o in recent]), _median([o.latency for o in baseline])
        if can_compare and r_lat and b_lat and b_lat > 0:
            ratio = r_lat / b_lat
            sig["latency ratio"] = round(ratio, 2)
            sev["latency"] = _grade(ratio, self.th["latency_ratio_warn"], self.th["latency_ratio_alert"])
        else:
            sev["latency"] = 0.0

        # 5) success rate drop
        r_ok = sum(1 for o in recent if o.ok) / len(recent)
        sig["recent success rate"] = round(r_ok, 3)
        if can_compare:
            b_ok = sum(1 for o in baseline if o.ok) / len(baseline)
            drop = b_ok - r_ok
            sig["success rate drop"] = round(drop, 3)
            sev["success"] = _grade(drop, self.th["success_drop_warn"], self.th["success_drop_alert"])
        else:
            sev["success"] = 0.0

        score = int(round(sum(WEIGHTS[k] * sev.get(k, 0.0) for k in WEIGHTS)))
        # Honeypot hits are **hard evidence** (elements invisible to humans are only touched by automation),
        # and cannot be diluted by "normal" readings from other signals.
        # By weight alone they are worth only 12 points, which would fall into the "normal" range —
        # contradicting this module calling them hard evidence.
        if hp:
            score = max(score, 40)                  # one hit immediately enters warning range
        score = max(0, min(100, score))

        if score >= 60:
            level, advice = "danger", (
                "Multiple leading indicators degrading at once — you are most likely already "
                "de-ranked. **Stop now**, switch account / IP, and let it cool for a few hours.")
        elif score >= 35:
            level, advice = "warning", (
                "Clear degradation trend. Halve your rate now, shrink batches, pause "
                "interactions, and watch whether it recovers.")
        elif score >= 15:
            level, advice = "watch", "Early signs of degradation. Ease off a little and watch the next window closely."
        else:
            level, advice = "normal", "No sign of a shadow ban. Current pace is fine."

        if hp:
            advice = f"⚠ Honeypot hit {hp} time(s) — hidden elements are only ever touched by automation. This is conclusive." + advice
        if not can_compare:
            advice += (f" (Note: baseline has only {len(baseline)} observation(s), so the "
                       f"completeness / latency / success-rate trend comparison is not active yet.)")

        return Verdict(level=level, score=score, advice=advice, signals=sig, samples=n)

    def summary(self) -> str:
        v = self.assess()
        parts = " | ".join(f"{k}={val}" for k, val in v.signals.items())
        return f"[soft-ban radar] {v.level}({v.score}/100) samples={v.samples}  {parts}"

    def reset(self) -> None:
        """Call after switching account/IP: old baseline no longer applies, clear and rebuild."""
        self._obs = []
        self._save()
