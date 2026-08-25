#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_interaction.py — interaction_policy and human_interaction unit tests

Usage:
  python tests/test_interaction.py

Test coverage:
  1. interaction_policy: daily limit / min gap anti-rapid-like / cross-day reset / conservative cut to 1/3
  2. human_interaction: dry_run safety valve (Bezier move mouse.move but no mouse.down/up)
"""

import asyncio
import os
import sys
import tempfile
import time

# Allow tests to run directly from repo root or inside tests/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
sys.path.insert(0, _SCRIPTS)

from interaction_policy import DEFAULT_LIMITS, MIN_GAP, Policy

# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════
_pass = 0
_fail = 0

def check(name, cond, detail=""):
    global _pass, _fail
    if cond:
        print(f"  PASS  {name}")
        _pass += 1
    else:
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        _fail += 1

def tmp_state():
    """Return a temporary state file path (auto-deleted after test)."""
    fd, path = tempfile.mkstemp(suffix=".json", prefix="mirage_test_")
    os.close(fd)
    os.unlink(path)   # Policy creates it itself; we only need the path
    return path


# ════════════════════════════════════════════════════════════════════
# 1. interaction_policy tests
# ════════════════════════════════════════════════════════════════════
def test_policy():
    print("\n── interaction_policy ──")

    # 1-a. Normal case: initially all can() should be True
    p = Policy(state_path=tmp_state())
    for action in DEFAULT_LIMITS:
        check(f"initial can({action})", p.can(action))

    # 1-b. Daily limit: after record reaches limit, can() returns False
    p2 = Policy(state_path=tmp_state(), limits={"like": 2, "follow": 1, "collect": 1, "comment": 1})
    # like limit=2: record twice consecutively (clear _last to bypass gap check)
    p2._last["like"] = 0   # reset last time so gap check passes
    p2.record("like")
    p2._last["like"] = 0
    p2.record("like")
    check("after over limit can(like)=False", not p2.can("like"))

    # 1-c. Min gap anti-rapid-like: immediately after record once, can() should be False
    p3 = Policy(state_path=tmp_state(), limits={"like": 200, "follow": 200, "collect": 200, "comment": 200})
    p3._last["like"] = 0   # ensure gap check passes so record works
    p3.record("like")
    # just recorded, _last["like"] = now, interval < MIN_GAP["like"](25s)
    check("immediately after record rapid-like guard can(like)=False", not p3.can("like"),
          f"MIN_GAP={MIN_GAP['like']}s, should be rejected right after record")

    # 1-d. Manually set _last far enough back, can() should become True again
    p3._last["like"] = time.time() - MIN_GAP["like"] - 1
    check("after enough gap can(like)=True", p3.can("like"))

    # 1-e. Cross-day reset: manually inject "yesterday" date + counts, after reload counts reset
    import json
    from datetime import date, timedelta
    yesterday = str(date.today() - timedelta(days=1))
    path = tmp_state()
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    # directly write a "yesterday" state file
    with open(path, "w") as f:
        json.dump({"date": yesterday, "counts": {"like": 999}, "last": {}}, f)
    p4 = Policy(state_path=path)
    check("cross-day reset: like count=0", p4._counts.get("like", 0) == 0,
          f"actual={p4._counts.get('like',0)}")
    check("after cross-day can(like)=True", p4.can("like"))

    # 1-f. conservative mode: limit cut to 1/3 (floor, minimum 1)
    p5 = Policy(state_path=tmp_state(), conservative=True)
    for k, orig in DEFAULT_LIMITS.items():
        expected = max(1, orig // 3)
        check(f"conservative {k} limit={expected}", p5.limits[k] == expected,
              f"actual={p5.limits[k]}")

    # 1-g. exhausted(): all actions reach limit
    p6 = Policy(state_path=tmp_state(), limits={"like": 1, "follow": 1, "collect": 1, "comment": 1})
    for action in p6.limits:
        p6._last[action] = 0
        p6.record(action)
    check("exhausted()=True when all actions hit limit", p6.exhausted())

    # 1-h. remaining() calculates correctly
    p7 = Policy(state_path=tmp_state(), limits={"like": 5, "follow": 3, "collect": 4, "comment": 2})
    p7._last["like"] = 0
    p7.record("like")   # like count -> 1
    rem = p7.remaining()
    check("remaining() like=4", rem["like"] == 4, f"actual={rem['like']}")
    check("remaining() follow=3", rem["follow"] == 3, f"actual={rem['follow']}")


# ════════════════════════════════════════════════════════════════════
# 2. human_interaction dry_run safety valve test
#    (use mock page instead of real Playwright page)
# ════════════════════════════════════════════════════════════════════
class MockMouse:
    """Record all mouse calls for assertions."""
    def __init__(self):
        self.moves = []
        self.downs = 0
        self.ups = 0

    async def move(self, x, y):
        self.moves.append((x, y))

    async def down(self):
        self.downs += 1

    async def up(self):
        self.ups += 1


class MockLocator:
    """Minimal usable locator mock: count/is_visible/bounding_box/scroll_into_view_if_needed/wait_for/click/get_attribute."""
    def __init__(self, visible=True, box=None, attr_val="false"):
        self._visible = visible
        self._box = box or {"x": 100, "y": 200, "width": 80, "height": 30}
        self._attr_val = attr_val

    async def count(self):
        return 1

    async def is_visible(self):
        return self._visible

    async def bounding_box(self):
        return self._box

    async def scroll_into_view_if_needed(self, timeout=3000):
        pass

    async def wait_for(self, state="visible", timeout=3000):
        pass

    async def click(self, trial=False, timeout=1500):
        pass   # trial=True has no side effects

    async def get_attribute(self, name):
        return self._attr_val


class MockPage:
    """Minimal Playwright page mock."""
    def __init__(self):
        self.mouse = MockMouse()
        self._locators = {}   # key -> MockLocator

    def locator(self, selector):
        # Return visible locator for the first selector; others return invisible (so _resolve hits the first one)
        return MockLocator(visible=True)

    def register_locator(self, selector, loc):
        self._locators[selector] = loc


def test_human_interaction_dry_run():
    """
    When dry_run=True:
      - _human_click must call mouse.move (Bezier move into place)
      - Never call mouse.down / mouse.up (no real click)
    When dry_run=False (mock simulation):
      - mouse.down and mouse.up each called once
    """
    print("\n── human_interaction dry_run safety valve ──")

    # human_behavior's human_mouse_move needs real page.mouse,
    # so we monkeypatch it under scripts/ path with a simple version.
    import types

    # Build a minimal human_behavior stub so import succeeds
    stub = types.ModuleType("human_behavior")

    async def _stub_human_mouse_move(page, tx, ty, start=(None, None)):
        """stub: call page.mouse.move directly and return end coordinates."""
        await page.mouse.move(tx, ty)
        return (tx, ty)

    async def _stub_human_sleep(base, lo=0, hi=0):
        pass

    stub.human_mouse_move = _stub_human_mouse_move
    stub.human_sleep = _stub_human_sleep
    sys.modules["human_behavior"] = stub

    # Reload human_interaction so its import hits the stub
    if "human_interaction" in sys.modules:
        del sys.modules["human_interaction"]
    from human_interaction import XhsInteractor

    # -- test dry_run=True --
    async def _test_dry():
        page = MockPage()
        interactor = XhsInteractor(page, dry_run=True)
        loc = MockLocator()
        clicked = await interactor._human_click(loc, "like")
        return page.mouse, clicked

    mouse_dry, clicked_dry = asyncio.run(_test_dry())

    check("dry_run=True: mouse.move called (Bezier to target)",
          len(mouse_dry.moves) > 0,
          f"moves={mouse_dry.moves}")
    check("dry_run=True: mouse.down not called (no real click)",
          mouse_dry.downs == 0,
          f"downs={mouse_dry.downs}")
    check("dry_run=True: mouse.up not called (no real click)",
          mouse_dry.ups == 0,
          f"ups={mouse_dry.ups}")
    check("dry_run=True: _human_click returns False",
          clicked_dry is False)

    # -- test dry_run=False --
    async def _test_real():
        page = MockPage()
        interactor = XhsInteractor(page, dry_run=False)
        loc = MockLocator()
        clicked = await interactor._human_click(loc, "like")
        return page.mouse, clicked

    mouse_real, clicked_real = asyncio.run(_test_real())

    check("dry_run=False: mouse.move called",
          len(mouse_real.moves) > 0)
    check("dry_run=False: mouse.down called once",
          mouse_real.downs == 1,
          f"downs={mouse_real.downs}")
    check("dry_run=False: mouse.up called once",
          mouse_real.ups == 1,
          f"ups={mouse_real.ups}")
    check("dry_run=False: _human_click returns True",
          clicked_real is True)

    # Clean up stub
    del sys.modules["human_behavior"]
    if "human_interaction" in sys.modules:
        del sys.modules["human_interaction"]


# ════════════════════════════════════════════════════════════════════
# Main entry point
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    test_policy()
    test_human_interaction_dry_run()

    print(f"\n{'='*40}")
    total = _pass + _fail
    print(f"Result: {_pass}/{total} PASS, {_fail} FAIL")
    if _fail:
        print("FAIL")
        sys.exit(1)
    else:
        print("PASS")
        sys.exit(0)
