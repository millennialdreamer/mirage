# -*- coding: utf-8 -*-
"""
human_interaction.py — Mirage interaction engine: identify and click "like a human" on platform pages
(like / follow / collect / comment). Currently deeply validated platform: Xiaohongshu (xhs).
Other platforms (dy/bili etc.) selectors are semantic reasonable guesses, **need to be checked and adjusted against actual pages**.

⚠️ Three safety iron rules (written into code, not reliant on self-discipline):
  1. **dry_run defaults to True** —— by default only moves mouse to target via Bezier, prints what would be done, but **does not
  actually click**.
     Only explicit `XhsInteractor(page, dry_run=False)` will truly interact.
  2. Every action first asks `policy.can(action)` —— skips if daily limit exceeded / cooldown not over.
  3. Interaction has **real external consequences** (actually likes/follows/comments strangers), **use only a throwaway account**,
  AI never runs it for real itself.

Design: recognition layer (multiple fallback selectors) → readiness check → Bezier move + hover + real click → verify effect.
Mouse trajectory reuses human_behavior's Bezier (never teleports).
"""

import asyncio
import random

try:                                              # when running directly under scripts/
    from human_behavior import human_mouse_move, human_sleep
except ImportError:
    try:                                          # after deployment to MediaCrawler/tools/
        from tools.human_behavior import human_mouse_move, human_sleep
    except ImportError:                           # in mirage package context after pip install
        from mirage.human_behavior import human_mouse_move, human_sleep


# Multi-platform element fallback selectors. Structure: {platform: {element: [selector list]}}
# Order = attempt order: stable semantic attribute → role/text → class fallback.
# ⚠️ xhs has been verified on actual pages; dy / bili are semantic reasonable guesses, **need to be checked and adjusted against
# actual pages**.
SELECTORS = {
    # -----------------------------------------------------------------------
    # Xiaohongshu (xhs) —— verified on actual pages
    # -----------------------------------------------------------------------
    "xhs": {
        "note_card":    ["section.note-item", "a[href*='/explore/']", "[data-type='note']"],
        "like":         ["[aria-label*='赞']", "[aria-label*='like']",
                         "span.like-wrapper", ".interact-container .like-active, .interact-container .like"],
        "collect":      ["[aria-label*='收藏']", "span.collect-wrapper", ".collect"],
        "follow":       ["button:has-text('关注'):not(:has-text('已关注'))",
                         "[aria-label='关注']", ".follow-button:not(.followed)"],
        "comment_box":  ["[contenteditable='true']", "textarea[placeholder*='评论']",
                         "div.comment-input"],
        "comment_send": ["button:has-text('发送')", "button:has-text('发布')", ".submit"],
    },

    # -----------------------------------------------------------------------
    # Douyin (dy) —— ⚠️ semantic guess, need to check and adjust against actual pages
    # Douyin web version (douyin.com) DOM structure changes frequently with versions; the following is a general semantic-attribute-
    # first strategy
    # -----------------------------------------------------------------------
    "dy": {
        "note_card":    ["[data-e2e='feed-active-video']", ".video-feed-item",
                         "[data-testid='video-item']"],
        "like":         # Like: aria-label is most stable, then data-e2e, class fallback
                        ["[aria-label*='点赞']", "[aria-label*='like']",
                         "[data-e2e='like-icon']", ".like-button",
                         "button:has-text('赞')"],  # ⚠️ needs verification
        "follow":       # Follow: text-content is most semantic, exclude "already followed" for unfollowed state
                        ["button:has-text('关注'):not(:has-text('已关注'))",
                         "[data-e2e='follow-button']", "[aria-label='关注']",
                         ".follow-button:not(.disabled)"],  # ⚠️ needs verification
        "comment_box":  ["[data-e2e='comment-input']", "[contenteditable='true']",
                         "textarea[placeholder*='评论']", ".comment-input-inner"],
        "comment_send": ["button:has-text('发送')", "[data-e2e='comment-send']",
                         "button:has-text('发布')"],
    },

    # -----------------------------------------------------------------------
    # Bilibili (bili) —— ⚠️ semantic guess, need to check and adjust against actual pages
    # Bilibili (bilibili.com) web version wbi signature is relatively simple, DOM relatively stable but still needs verification
    # -----------------------------------------------------------------------
    "bili": {
        "note_card":    [".bili-video-card", ".video-card", "[data-report='click']"],
        "like":         # Bilibili like is in the player page toolbar, usually has aria-label
                        ["[aria-label*='点赞']", "[aria-label*='like']",
                         ".video-like", ".like.on, .like",
                         "button.like-btn"],  # ⚠️ needs verification
        "follow":       # Bilibili follow is next to the uploader avatar; unfollowed state is a "Follow" button
                        ["button:has-text('关注'):not(:has-text('已关注'))",
                         ".follow-btn:not(.be-follow-btn--followed)",
                         "[aria-label='关注']", ".b-btn--follow"],  # ⚠️ needs verification
        "comment_box":  ["#comment-box", "textarea[placeholder*='发一条友善的评论']",
                         "[contenteditable='true']", ".comment-send input"],
        "comment_send": ["button:has-text('发布')", ".comment-submit",
                         "button:has-text('发送')"],
    },
}


class XhsInteractor:
    """Multi-platform human-like interactor. Holds a Playwright page.

    Backward compatibility: if platform is not passed, defaults to 'xhs', behavior identical to old version.

    Parameters:
        page:     Playwright Page object
        policy:   interaction quota policy (optional)
        dry_run:  defaults True, only demo no real click; pass False explicitly to truly interact
        platform: platform code, supports 'xhs'/'dy'/'bili' (default 'xhs')
    """

    def __init__(self, page, policy=None, dry_run=True, platform="xhs"):
        self.page = page
        self.policy = policy
        self.dry_run = dry_run          # default: only demo, no real click
        self.platform = platform        # platform selector branch
        self._mouse = (None, None)      # maintain last mouse position for more coherent Bezier chaining
        # take the corresponding platform from nested SELECTORS, fallback to xhs
        self._selectors = SELECTORS.get(platform, SELECTORS["xhs"])

    # ---- recognition layer: multiple fallback ----
    async def _resolve(self, key):
        """Find the first visible element in order of SELECTORS[key] for current platform; return None if none found."""
        for sel in self._selectors.get(key, []):
            try:
                loc = self.page.locator(sel).first
                if await loc.count() and await loc.is_visible():
                    return loc
            except Exception:
                continue
        return None

    # ---- readiness check: scroll into viewport + visible + not occluded ----
    async def _ready(self, loc):
        try:
            await loc.scroll_into_view_if_needed(timeout=3000)
            await loc.wait_for(state="visible", timeout=3000)
            await loc.click(trial=True, timeout=1500)   # side-effect-free trial click; raises if occluded
            return True
        except Exception:
            return False

    # ---- click layer: Bezier move → hover hesitation → (dry-run? stop : real click) ----
    async def _human_click(self, loc, label=""):
        box = await loc.bounding_box()
        if not box:
            return False
        tx = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
        ty = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
        # Bezier move to target (not teleport), maintain last position for chaining
        self._mouse = await human_mouse_move(self.page, tx, ty, start=self._mouse)
        await asyncio.sleep(random.uniform(0.15, 0.5))   # pre-click hover hesitation, like a human
        if self.dry_run:
            print(f"  [dry-run] would click 「{label}」@({tx:.0f},{ty:.0f})——moved into place, not actually clicking")
            return False
        # real synthetic click (mousedown→pause→mouseup)
        await self.page.mouse.down()
        await asyncio.sleep(random.uniform(0.05, 0.09))
        await self.page.mouse.up()
        return True

    async def _attr(self, loc, name):
        try:
            return await loc.get_attribute(name)
        except Exception:
            return None

    # Different platforms use different attributes to express "liked/collected/followed": Xiaohongshu mostly uses class (.like-
    # active etc.) +
    # aria-label text changes, a few use aria-pressed. Checking only a single attribute can misjudge as "success" when absent.
    VERIFY_ATTRS = ("aria-pressed", "class", "aria-label", "aria-selected")

    async def _state_snapshot(self, loc):
        """Take a snapshot of multiple attributes that may reflect state, for before/after click comparison."""
        snap = {}
        for name in self.VERIFY_ATTRS:
            snap[name] = await self._attr(loc, name)
        return snap

    # ---- action layer: each action first checks quota, then readiness, then human-like click, then verify ----
    async def _do(self, key, label):
        if self.policy and not self.policy.can(key):
            print(f"  「{label}」has reached limit or is cooling down, skip")
            return False
        loc = await self._resolve(key)
        if not loc:
            print(f"  did not find 「{label}」 button (selector needs adjustment against actual page, see SELECTORS)")
            return False
        if not await self._ready(loc):
            print(f"  「{label}」 is not clickable (occluded/invisible)")
            return False
        before = await self._state_snapshot(loc)
        clicked = await self._human_click(loc, label)
        if not clicked:                              # dry-run or failed to click
            return False
        await human_sleep(0.6, 0.5, 1.2)             # natural short pause after click
        after = await self._state_snapshot(loc)

        # Three-state honest verdict (old implementation: only checked aria-pressed; Xiaohongshu like button doesn't even have this
        # attribute → before=None
        # → always judged "took effect", reported success even when not clicked and still deducted quota, making the verification
        # layer useless).
        verifiable = any(v is not None for v in before.values())
        changed = any(before[k] != after[k] for k in before)
        if not verifiable:
            state = "clicked (button has no verifiable attribute, whether it took effect unknown)"
        elif changed:
            state = "took effect"
        else:
            state = "no state change observed (may not have clicked successfully)"

        # Quota: count as long as a real click was dispatched (better to over-count——under-counting would let actual interactions
        # exceed quota limits,
        # which raises ban risk; this matches this tool's "better slow" stance).
        if self.policy:
            self.policy.record(key)
        print(f"  {'✓' if changed else '·'} 「{label}」{state}")
        return clicked

    async def like_note(self):
        return await self._do("like", "like")

    async def collect_note(self):
        return await self._do("collect", "collect")

    async def follow_user(self):
        return await self._do("follow", "follow")

    async def comment_note(self, text: str):
        """Comment — the most sensitive action (content moderation flags repeats, ad
        wording and links first). Typing character by character reads as more human."""
        if self.policy and not self.policy.can("comment"):
            print("  「comment」has reached limit or is cooling down, skip")
            return False
        box = await self._resolve("comment_box")
        if not box:
            print("  comment box not found")
            return False
        if not await self._ready(box):
            return False
        await self._human_click(box, "comment box")
        if self.dry_run:
            print(f"  [dry-run] would type comment character by character: {text!r} (not actually sending)")
            return False
        await box.click()
        for ch in text:                              # character by character + random delay, like human typing
            await self.page.keyboard.type(ch)
            await asyncio.sleep(random.uniform(0.06, 0.22))
        await human_sleep(1.0, 0.6, 1.5)             # pause before sending (as if checking)
        send = await self._resolve("comment_send")
        if send and await self._human_click(send, "send comment"):
            if self.policy:
                self.policy.record("comment")
            print("  ✓ comment sent")
            return True
        return False
