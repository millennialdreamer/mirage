#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_interaction.py — interaction_policy 与 human_interaction 单元测试

运行方式：
  python tests/test_interaction.py

测试覆盖：
  1. interaction_policy：每日上限 / 最小间隔防秒赞 / 跨天清零 / conservative 砍 1/3
  2. human_interaction：dry_run 安全阀（贝塞尔移动 mouse.move 但不调 mouse.down/up）
"""

import asyncio
import os
import sys
import tempfile
import time

# 让测试可从 repo 根目录 or tests/ 内直接跑
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
sys.path.insert(0, _SCRIPTS)

from interaction_policy import Policy, DEFAULT_LIMITS, MIN_GAP

# ════════════════════════════════════════════════════════════════════
# 辅助
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
    """返回一个临时 state 文件路径（测试结束后自动删除）。"""
    fd, path = tempfile.mkstemp(suffix=".json", prefix="mirage_test_")
    os.close(fd)
    os.unlink(path)   # Policy 自己会创建；我们只要路径
    return path


# ════════════════════════════════════════════════════════════════════
# 1. interaction_policy 测试
# ════════════════════════════════════════════════════════════════════
def test_policy():
    print("\n── interaction_policy ──")

    # 1-a. 正常情况：初始时应全部 can()
    p = Policy(state_path=tmp_state())
    for action in DEFAULT_LIMITS:
        check(f"初始 can({action})", p.can(action))

    # 1-b. 每日上限：record 到上限后 can() 返回 False
    p2 = Policy(state_path=tmp_state(), limits={"like": 2, "follow": 1, "collect": 1, "comment": 1})
    # like 上限=2：连续record两次（用 _last 清零绕过间隔检查）
    p2._last["like"] = 0   # 重置上次时间让间隔检查通过
    p2.record("like")
    p2._last["like"] = 0
    p2.record("like")
    check("超上限后 can(like)=False", not p2.can("like"))

    # 1-c. 最小间隔防秒赞：record 一次后立刻 can() 应为 False
    p3 = Policy(state_path=tmp_state(), limits={"like": 200, "follow": 200, "collect": 200, "comment": 200})
    p3._last["like"] = 0   # 确保间隔检查通过，可以 record
    p3.record("like")
    # 刚 record 完，_last["like"] = now，间隔 < MIN_GAP["like"](25s)
    check("刚 record 后秒赞防护 can(like)=False", not p3.can("like"),
          f"MIN_GAP={MIN_GAP['like']}s，刚记录应被拒绝")

    # 1-d. 手动把 _last 拨到足够久以前，can() 应恢复 True
    p3._last["like"] = time.time() - MIN_GAP["like"] - 1
    check("间隔足够后 can(like)=True", p3.can("like"))

    # 1-e. 跨天清零：手动注入 "昨天" 的 date + 计数，重新加载后计数归零
    from datetime import date, timedelta
    import json
    yesterday = str(date.today() - timedelta(days=1))
    path = tmp_state()
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    # 直接写一个"昨天"的 state 文件
    with open(path, "w") as f:
        json.dump({"date": yesterday, "counts": {"like": 999}, "last": {}}, f)
    p4 = Policy(state_path=path)
    check("跨天清零：like count=0", p4._counts.get("like", 0) == 0,
          f"实际={p4._counts.get('like',0)}")
    check("跨天后 can(like)=True", p4.can("like"))

    # 1-f. conservative 模式：上限砍到 1/3（向下取整，最小 1）
    p5 = Policy(state_path=tmp_state(), conservative=True)
    for k, orig in DEFAULT_LIMITS.items():
        expected = max(1, orig // 3)
        check(f"conservative {k} 上限={expected}", p5.limits[k] == expected,
              f"实际={p5.limits[k]}")

    # 1-g. exhausted()：所有动作都到上限
    p6 = Policy(state_path=tmp_state(), limits={"like": 1, "follow": 1, "collect": 1, "comment": 1})
    for action in p6.limits:
        p6._last[action] = 0
        p6.record(action)
    check("exhausted()=True 当所有动作达上限", p6.exhausted())

    # 1-h. remaining() 正确计算
    p7 = Policy(state_path=tmp_state(), limits={"like": 5, "follow": 3, "collect": 4, "comment": 2})
    p7._last["like"] = 0
    p7.record("like")   # like count -> 1
    rem = p7.remaining()
    check("remaining() like=4", rem["like"] == 4, f"实际={rem['like']}")
    check("remaining() follow=3", rem["follow"] == 3, f"实际={rem['follow']}")


# ════════════════════════════════════════════════════════════════════
# 2. human_interaction dry_run 安全阀测试
#    （用 mock page 替代真实 Playwright page）
# ════════════════════════════════════════════════════════════════════
class MockMouse:
    """记录所有 mouse 调用，供断言用。"""
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
    """最小可用 locator mock：count/is_visible/bounding_box/scroll_into_view_if_needed/wait_for/click/get_attribute。"""
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
        pass   # trial=True 无副作用

    async def get_attribute(self, name):
        return self._attr_val


class MockPage:
    """最小 Playwright page mock。"""
    def __init__(self):
        self.mouse = MockMouse()
        self._locators = {}   # key -> MockLocator

    def locator(self, selector):
        # 对第一个 selector 返回可见 locator，其余返回不可见的（让 _resolve 用第一个命中）
        return MockLocator(visible=True)

    def register_locator(self, selector, loc):
        self._locators[selector] = loc


def test_human_interaction_dry_run():
    """
    dry_run=True 时：
      - _human_click 必须调用 mouse.move（贝塞尔移动到位）
      - 绝不调用 mouse.down / mouse.up（不真点）
    dry_run=False 时（mock 模拟）：
      - mouse.down 和 mouse.up 各调用一次
    """
    print("\n── human_interaction dry_run 安全阀 ──")

    # human_behavior 的 human_mouse_move 需要真实 page.mouse，
    # 我们在 scripts/ 路径下 monkeypatch 它，用一个简单版本替代。
    import importlib
    import types

    # 构造一个最小的 human_behavior stub，使 import 成功
    stub = types.ModuleType("human_behavior")

    async def _stub_human_mouse_move(page, tx, ty, start=(None, None)):
        """stub：直接调用 page.mouse.move，返回终点坐标。"""
        await page.mouse.move(tx, ty)
        return (tx, ty)

    async def _stub_human_sleep(base, lo=0, hi=0):
        pass

    stub.human_mouse_move = _stub_human_mouse_move
    stub.human_sleep = _stub_human_sleep
    sys.modules["human_behavior"] = stub

    # 重新加载 human_interaction，使其 import 命中 stub
    if "human_interaction" in sys.modules:
        del sys.modules["human_interaction"]
    from human_interaction import XhsInteractor

    # —— 测试 dry_run=True ——
    async def _test_dry():
        page = MockPage()
        interactor = XhsInteractor(page, dry_run=True)
        loc = MockLocator()
        clicked = await interactor._human_click(loc, "点赞")
        return page.mouse, clicked

    mouse_dry, clicked_dry = asyncio.run(_test_dry())

    check("dry_run=True: mouse.move 被调用（贝塞尔到位）",
          len(mouse_dry.moves) > 0,
          f"moves={mouse_dry.moves}")
    check("dry_run=True: 不调 mouse.down（不真点）",
          mouse_dry.downs == 0,
          f"downs={mouse_dry.downs}")
    check("dry_run=True: 不调 mouse.up（不真点）",
          mouse_dry.ups == 0,
          f"ups={mouse_dry.ups}")
    check("dry_run=True: _human_click 返回 False",
          clicked_dry is False)

    # —— 测试 dry_run=False ——
    async def _test_real():
        page = MockPage()
        interactor = XhsInteractor(page, dry_run=False)
        loc = MockLocator()
        clicked = await interactor._human_click(loc, "点赞")
        return page.mouse, clicked

    mouse_real, clicked_real = asyncio.run(_test_real())

    check("dry_run=False: mouse.move 被调用",
          len(mouse_real.moves) > 0)
    check("dry_run=False: mouse.down 调用一次",
          mouse_real.downs == 1,
          f"downs={mouse_real.downs}")
    check("dry_run=False: mouse.up 调用一次",
          mouse_real.ups == 1,
          f"ups={mouse_real.ups}")
    check("dry_run=False: _human_click 返回 True",
          clicked_real is True)

    # 清理 stub
    del sys.modules["human_behavior"]
    if "human_interaction" in sys.modules:
        del sys.modules["human_interaction"]


# ════════════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    test_policy()
    test_human_interaction_dry_run()

    print(f"\n{'='*40}")
    total = _pass + _fail
    print(f"结果：{_pass}/{total} PASS，{_fail} FAIL")
    if _fail:
        print("FAIL")
        sys.exit(1)
    else:
        print("PASS")
        sys.exit(0)
