# -*- coding: utf-8 -*-
"""
human_behavior.py — Reusable "human behavior simulation" tools (Bezier mouse + human-like rhythm).

The L5 method injected by apply_hardening.py into core.py directly calls this module (single source of truth),
so improvements here automatically benefit the injected version. Can also be manually integrated:

    from tools.human_behavior import human_sleep, warmup, simulate_page_activity

    await warmup()                       # Pause a few seconds after opening the page
    ...
    await simulate_page_activity(page)   # Between pages: Bezier mouse movement + scrolling + reading pause
    await human_sleep(config.CRAWLER_MAX_SLEEP_SEC)   # Sleep with jitter + occasional long pauses

Design principles (after anti-crawler expert review):
  - Mouse never teleports. Teleport = straight zero-trace infinite speed, more bot-like than "no movement".
    Always use Bezier curves, stepwise interpolation, micro-noise per step, accelerate → decelerate.
  - Time intervals are not just uniform random, but "mostly short + occasional long pauses", matching real human log-normal distribution.
  - Any exception is swallowed, never interrupts the main crawl flow.
"""

import asyncio
import random


def _bezier_path(x0, y0, x1, y1, steps):
    """Generate cubic Bezier path points from (x0,y0) to (x1,y1) (two random control points → natural arc)."""
    dx, dy = x1 - x0, y1 - y0
    cx1 = x0 + dx * random.uniform(0.2, 0.4) + random.uniform(-40, 40)
    cy1 = y0 + dy * random.uniform(0.2, 0.4) + random.uniform(-40, 40)
    cx2 = x0 + dx * random.uniform(0.6, 0.8) + random.uniform(-40, 40)
    cy2 = y0 + dy * random.uniform(0.6, 0.8) + random.uniform(-40, 40)
    pts = []
    for i in range(1, steps + 1):
        # Ease in/out (smoothstep): remap uniform i/steps into "slow start → fast mid → decelerate before target".
        # ⚠️ Using uniform t directly makes the whole trajectory nearly constant speed and endpoint velocity nonzero—this is
        # the most typical bot feature in kinematics (humans follow Fitts's law: accelerate when approaching, significantly
        # decelerate near target). Risk-control systems that model behavior
        # (reCAPTCHA v3 / Ruishu etc.) check exactly this speed curve, so this line is the key to human-like trajectory.
        _u = i / steps
        t = _u * _u * (3 - 2 * _u)
        mt = 1 - t
        bx = mt**3 * x0 + 3 * mt**2 * t * cx1 + 3 * mt * t**2 * cx2 + t**3 * x1
        by = mt**3 * y0 + 3 * mt**2 * t * cy1 + 3 * mt * t**2 * cy2 + t**3 * y1
        pts.append((bx, by))
    return pts


async def human_mouse_move(page, x, y, start=(None, None), steps=None):
    """Move mouse from start to (x,y) along a Bezier curve, stepwise + micro-noise + random delay between steps.

    When start is omitted, use a random starting point (first movement). Return the ending point for chaining to maintain last position.
    """
    x0, y0 = start
    if x0 is None:
        x0, y0 = random.randint(100, 1000), random.randint(100, 600)
    steps = steps or random.randint(8, 16)
    for bx, by in _bezier_path(x0, y0, x, y, steps):
        await page.mouse.move(bx + random.uniform(-1.5, 1.5),
                              by + random.uniform(-1.5, 1.5))
        # Step intervals also follow a right-skewed distribution: human hand speed varies, with occasional micro-pauses; uniform
        # step timing is also a statistically detectable flaw.
        await asyncio.sleep(human_delay(0.019, sigma=0.35, lo=0.5, hi=2.6))
    return (x, y)


def human_delay(base_sec: float, sigma: float = 0.45,
                lo: float = 0.55, hi: float = 3.5) -> float:
    """Return a **right-skewed (log-normal)** duration: median = base_sec, most slightly shorter, occasionally much longer.

    Why not random.uniform: human time intervals are naturally right-skewed (many short intervals + a few long tails),
    while the histogram of a uniform distribution is a **flat-topped rectangle**—statistically obviously fake; the KS test can
    directly distinguish it from humans.
    Previously it used an "85% short uniform + 15% long uniform" approximation, whose histogram is two rectangles and can still be detected;
    now it directly samples log-normal, producing a genuinely smooth right-skewed curve.

    lo/hi are soft clamps relative to base (preventing extreme values), without changing the main shape.
    """
    d = base_sec * random.lognormvariate(0, sigma)
    return max(base_sec * lo, min(base_sec * hi, d))


async def human_sleep(base_sec: float, lo: float = 0.7, hi: float = 1.6) -> None:
    """Sleep with right-skewed jitter (log-normal). lo/hi are soft clamp boundaries; the long tail can exceed hi.

    Example: base=6 → median 6s, mostly 4~9s, occasionally teens of seconds (human distraction/reading).
    """
    await asyncio.sleep(human_delay(base_sec, sigma=0.45, lo=lo * 0.8, hi=hi * 2.2))


async def warmup(min_sec: float = 3.0, max_sec: float = 8.0) -> None:
    """Warm-up pause before the first action. Humans look at a page for a few seconds after opening it; bots immediately start searching."""
    mid = (min_sec + max_sec) / 2                    # Use interval midpoint as median, sample right-skewed
    await asyncio.sleep(human_delay(mid, sigma=0.40,
                                    lo=min_sec / mid, hi=max_sec * 1.8 / mid))


async def simulate_page_activity(page) -> None:
    """Human-like behavior between page turns: Bezier mouse movement to 2–4 points + scrolling + reading pause + occasional scroll-back.

    Fills the strong bot signal of "completely static page during sleep", and the mouse moves in natural arcs rather than teleporting.
    Any exception is swallowed, never affects the main crawl flow.
    """
    try:
        last = (None, None)
        # Scroll down, like browsing a result list
        await page.mouse.wheel(0, random.randint(300, 700))
        await asyncio.sleep(random.uniform(0.4, 1.0))

        # Bezier move to 2–4 random positions (natural arc, maintain last position for chaining)
        for _ in range(random.randint(2, 4)):
            tx, ty = random.randint(150, 1200), random.randint(120, 700)
            last = await human_mouse_move(page, tx, ty, start=last)
            await asyncio.sleep(random.uniform(0.15, 0.5))

        # Reading pause: stop for a while after scrolling to a batch of content (humans are reading)
        await asyncio.sleep(random.uniform(0.8, 2.2))

        # About 40% probability to scroll back a little (natural review)
        if random.random() < 0.4:
            await page.mouse.wheel(0, -random.randint(80, 250))
            await asyncio.sleep(random.uniform(0.2, 0.6))
    except Exception:
        pass


async def human_hover(page, selector: str) -> None:
    """Optional enhancement: hover over an element (no click, no navigation, safe).

    Risk control values the "hover → hesitation" decision chain. Hover does not trigger navigation, safer than click,
    suitable for manual integration (e.g., hovering over note card titles). selector is provided by the caller according to the page
    structure.
    """
    try:
        await page.hover(selector, timeout=3000)
        await asyncio.sleep(random.uniform(0.3, 1.2))
    except Exception:
        pass
