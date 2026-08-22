# -*- coding: utf-8 -*-
"""
Behavior-layer core invariant regression tests.

These assertions guard the **statistical and logical correctness** of
"human-like" as a core selling point -- each of them was once a real bug:
  - Bezier used uniform t sampling → roughly constant speed over the whole path
    (kinematically the most typical robot signature)
  - Intervals used random.uniform everywhere → histogram was a flat-top
    rectangle, instantly exposed by a KS test
  - Like validation always returned True → "took effect" was reported even when
    it didn't, and quota was still deducted
  - Honeypot hits were diluted by other normal signals into "normal"
    (contradicting the qualitative definition of "conclusive evidence")
Once someone breaks these, this file must turn red.
"""
import asyncio
import math
import os
import random
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import human_behavior as hb  # noqa: E402
from device_profile import DeviceProfile  # noqa: E402
from soft_ban_radar import SoftBanRadar  # noqa: E402


# ── Mouse trajectory: must ease in/out, never constant speed ──────────────────────────
def test_bezier_is_eased_not_constant_speed():
    random.seed(42)
    pts, prev, dists = hb._bezier_path(0, 0, 1000, 0, 20), (0.0, 0.0), []
    for p in pts:
        dists.append(math.dist(prev, p))
        prev = p
    head = sum(dists[:4]) / 4
    mid = sum(dists[8:12]) / 4
    tail = sum(dists[-4:]) / 4
    assert mid > head * 1.5, f"mid should be significantly faster than start (ease-in): start {head:.1f} mid {mid:.1f}"
    assert mid > tail * 1.5, f"mid should be significantly faster than end (ease-out): end {tail:.1f} mid {mid:.1f}"


# ── Timing distribution: must be right-skewed, not a flat-top rectangle ────────────────────────
def _skew(xs):
    m, sd = statistics.mean(xs), statistics.pstdev(xs)
    return sum(((x - m) / sd) ** 3 for x in xs) / len(xs)


def test_delay_distribution_is_right_skewed():
    random.seed(1)
    samples = [hb.human_delay(6.0) for _ in range(8000)]
    assert _skew(samples) > 0.5, "Intervals must be right-skewed (human shape), not uniform distribution"
    assert 5.4 < statistics.median(samples) < 6.6, "Median should be anchored near base"


# ── Soft-ban radar ────────────────────────────────────────────
def _radar(account):
    return SoftBanRadar(state_path=os.path.join(tempfile.mkdtemp(), "r.json"), account=account)


def test_radar_refuses_to_guess_on_small_sample():
    r = _radar("few")
    for _ in range(5):
        r.observe(ok=True, latency=1.0, completeness=1.0)
    assert r.assess().level == "数据不足", "On insufficient samples the radar must say insufficient data, never guess"


def test_radar_no_false_alarm_on_healthy_stream():
    r = _radar("ok")
    for _ in range(40):
        r.observe(ok=True, latency=1.0, completeness=1.0)
    assert r.assess().level == "正常", "Healthy stream must not raise false alarms"


def test_radar_detects_degradation():
    r = _radar("bad")
    for _ in range(40):
        r.observe(ok=True, latency=1.0, completeness=1.0)
    for i in range(20):
        r.observe(ok=(i % 3 != 0), latency=2.8, completeness=0.7, captcha=(i % 5 == 0))
    v = r.assess()
    assert v.level in ("警戒", "危险") and v.should_slow_down()


def test_radar_detects_silent_shrink_alone():
    """When only the most hidden degradation signal -- "returned silent shrink" -- exists, it must still be noticed."""
    r = _radar("shrink")
    for _ in range(40):
        r.observe(ok=True, latency=1.0, completeness=1.0)
    for _ in range(20):
        r.observe(ok=True, latency=1.0, completeness=0.68)
    assert r.assess().level != "正常", "Silent shrink is the most typical soft-ban symptom, must not miss it"


def test_radar_honeypot_is_conclusive_not_diluted():
    """A honeypot hit is documented as "conclusive evidence", so it must not be diluted into "normal" by other normal signals."""
    r = _radar("hp")
    for _ in range(30):
        r.observe(ok=True, latency=1.0, completeness=1.0)
    r.observe(ok=True, latency=1.0, completeness=1.0, honeypot=True)
    v = r.assess()
    assert v.level in ("警戒", "危险"), "Honeypot is conclusive evidence, must be >= warning"


def test_radar_accounts_are_isolated():
    path = os.path.join(tempfile.mkdtemp(), "multi.json")
    a = SoftBanRadar(state_path=path, account="A")
    b = SoftBanRadar(state_path=path, account="B")
    for _ in range(20):
        a.observe(ok=False, captcha=True)
    assert b.assess().samples == 0, "Account baselines must be isolated"


# ── Device profile ──────────────────────────────────────────────
def test_profile_is_deterministic_and_unique():
    assert DeviceProfile.from_seed("s1").to_dict() == DeviceProfile.from_seed("s1").to_dict()
    assert DeviceProfile.from_seed("s1").noise_seed != DeviceProfile.from_seed("s2").noise_seed


def test_generated_profiles_are_always_self_consistent():
    """The generator must never produce self-contradictory profiles -- locally true but globally false is more dangerous than no change."""
    for i in range(120):
        p = DeviceProfile.from_seed(f"seed-{i}")
        assert not p.check(), f"seed-{i} produced an inconsistent profile: {p.check()}"


def test_consistency_checker_catches_contradictions():
    base = DeviceProfile.from_seed("seed-0").to_dict()
    win = next(DeviceProfile.from_seed(f"s{i}") for i in range(50)
               if "Windows" in DeviceProfile.from_seed(f"s{i}").os)
    for override in ({"webgl_renderer": "ANGLE (Apple, Apple M2, Metal)"},
                     {"platform": "MacIntel"}, {"languages": []}, {"cores": 128}):
        broken = DeviceProfile(**{**win.to_dict(), **override})
        assert broken.check(), f"validator missed contradiction: {override}"
    assert base  # Keep the reference to avoid a lint false positive


def test_init_script_covers_all_canvas_exits():
    js = DeviceProfile.from_seed("js").to_init_script()
    for must in ("getImageData", "toDataURL", "toBlob", "getParameter", "hardwareConcurrency"):
        assert must in js, f"injection script is missing {must} (canvas has three exits; blocking only one is caught by differential profiling)"


# ── Captcha hook: safe defaults must not degrade ───────────────────────────
class _FakePage:
    class _M:
        async def move(self, *a, **k): pass
        async def wheel(self, *a): pass
    mouse = _M()


def _loop(on_captcha=None, dry_run=False, danger_after=True):
    from mirage_loop import MirageLoop

    async def _ret(v):
        return v
    lp = MirageLoop(_FakePage(), dry_run=dry_run, on_captcha=on_captcha)
    lp.radar = None
    lp._danger = lambda: _ret(danger_after)
    return lp


def test_captcha_hook_safe_defaults():
    assert asyncio.run(_loop(None)._handle_captcha()) is False, "No callback must keep the loop stopped"
    assert asyncio.run(_loop(lambda p: False)._handle_captcha()) is False

    def boom(p):
        raise RuntimeError("captcha service is down")
    assert asyncio.run(_loop(boom)._handle_captcha()) is False, "Callback exception must not take down the main loop"


def test_captcha_hook_not_triggered_in_dry_run():
    calls = []
    lp = _loop(lambda p: calls.append(1) or True, dry_run=True)
    assert asyncio.run(lp._handle_captcha()) is False and not calls


def test_captcha_hook_does_not_trust_callback_blindly():
    """Callback claims it solved the captcha, but the post-check risk-control signal is still present → still stop."""
    assert asyncio.run(_loop(lambda p: True, danger_after=True)._handle_captcha()) is False


def test_captcha_hook_resumes_only_when_signal_cleared():
    assert asyncio.run(_loop(lambda p: True, danger_after=False)._handle_captcha()) is True
