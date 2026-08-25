# -*- coding: utf-8 -*-
"""
mirage_loop.py — Mirage ultimate "human-like account warming" main loop.

Not a "click-spam loop", but simulating a real person browsing Xiaohongshu: **heavy browsing + restrained interaction + natural pauses**.
Makes the whole session's behavior distribution resemble a real person, not high-frequency clicking — that is the real zero-ban path.

⚠️ Default dry-run (demo only, no real clicks). Each round first runs a risk-control circuit-breaker check. Only use alt accounts.
The AI never runs it for real.

Choreography: human_behavior(browse) + human_interaction(interact) + interaction_policy(quota).
"""

import asyncio
import inspect
import random
import time

try:
    from human_behavior import human_sleep, simulate_page_activity, warmup
    from human_interaction import XhsInteractor
    from interaction_policy import Policy
except ImportError:
    try:
        from tools.human_behavior import human_sleep, simulate_page_activity, warmup
        from tools.human_interaction import XhsInteractor
        from tools.interaction_policy import Policy
    except ImportError:                           # pip-installed mirage package context
        from mirage.human_behavior import human_sleep, simulate_page_activity, warmup
        from mirage.human_interaction import XhsInteractor
        from mirage.interaction_policy import Policy

try:
    from _logging import get_logger  # library module logging (don't use bare print)
except ImportError:                               # deployment/package context fallback: degrade to stdlib logger
    import logging as _logging_mod

    def get_logger(name: str = "mirage.loop"):
        _logging_mod.basicConfig(level=_logging_mod.INFO,
                                 format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        return _logging_mod.getLogger(name)

log = get_logger("mirage.loop")

try:                                              # soft ban radar (optional: if missing, degrade to no early warning)
    from soft_ban_radar import SoftBanRadar
except ImportError:
    try:
        from tools.soft_ban_radar import SoftBanRadar
    except ImportError:
        try:
            from mirage.soft_ban_radar import SoftBanRadar
        except ImportError:
            SoftBanRadar = None

# Risk-control signals: use **full phrases** (almost never appear in note body text), check dialogs first, massively reduce false positives.
# Counter-example: the standalone word "captcha" may appear in note body text → would falsely trigger circuit breaker, so don't use single
# words.
#
# ⚠️ DO NOT TRANSLATE the phrases below. They are the exact wording these Chinese-language
# platforms render in their risk-control dialogs ("acting too frequently", "complete the
# security check", "drag the slider", "your account has been ...", "please log in again").
# Translating them disables the circuit breaker completely — it would never match again,
# and the loop would keep interacting straight into a ban.
DANGER_PHRASES = ["操作过于频繁", "操作太频繁", "频繁操作请", "完成安全验证",
                  "账号存在异常", "账号出现异常", "系统检测到异常", "请完成验证",
                  "拖动滑块", "滑动验证", "你的账号已被", "账号已被封", "请重新登录"]
DANGER_DIALOG_SEL = ["[role=dialog]", ".reds-dialog", ".verify-dialog",
                     ".captcha-container", "[class*=captcha]", "[class*=verify]"]


class MirageLoop:
    def __init__(self, page, dry_run=True, interact_prob=0.15,
                 conservative=False, max_minutes=30,
                 platform_tz="Asia/Shanghai", on_captcha=None):
        """
        platform_tz — target platform's timezone (IANA name), passed through to Policy.
            When operating a domestic platform from overseas, use "Asia/Shanghai" (it follows the platform's active hours, not the
            operator's local time).

        on_captcha — optional callback `fn(page) -> bool` (may be async): called when a captcha is encountered.
            ⚠️ **Mirage does not solve captchas itself** (that's another track, already a red ocean with CapSolver/2Captcha etc.).
            Here it only provides "detect → hook → human-like refill timing": you connect a captcha service or handle it manually.
            Callback returning True means resolved; the loop will **insert a human-like pause** before continuing (a real person
            won't resume with 0 delay after solving a captcha — instant resume is itself a machine trait). Returning False / no
            callback → maintain "stop immediately".
        """
        self.page = page
        self.policy = Policy(conservative=conservative, platform_tz=platform_tz)
        self.actor = XhsInteractor(page, policy=self.policy, dry_run=dry_run)
        self.interact_prob = interact_prob          # probability of interacting after seeing a note (usually just browse)
        self.max_seconds = max_minutes * 60
        self.dry_run = dry_run
        # Soft-ban radar: _danger() is the emergency brake for "captcha already popped up"; the radar is its **early warning**
        # (detects trending downranking and slows down before the ban). The two are "early warning" vs "emergency brake".
        self.radar = SoftBanRadar() if SoftBanRadar else None
        self.on_captcha = on_captcha                # see docstring: Mirage does not solve, only hooks

    async def _danger(self):
        """Detect risk-control signals. Dialogs first (most reliable), then fall back to
        whole-phrase matching on the page. The circuit breaker has top priority."""
        # 1) Risk-control dialog / verification overlay — most reliable signal
        try:
            for sel in DANGER_DIALOG_SEL:
                d = self.page.locator(sel).first
                if await d.count() and await d.is_visible():
                    txt = (await d.inner_text())[:1000]
                    if any(p in txt for p in DANGER_PHRASES) or "验证" in txt or "安全" in txt:
                        return True
        except Exception:
            pass
        # 2) Full page only matches **complete phrases** (the standalone word "captcha" doesn't count, avoiding false positives from note
        # body text)
        try:
            body = (await self.page.inner_text("body"))[:5000]
            return any(p in body for p in DANGER_PHRASES)
        except Exception:
            return False

    async def _handle_captcha(self) -> bool:
        """On captcha: hand control to the user callback. **Mirage does not solve captchas itself**.

        Returns True only if the callback claims resolved and a re-check shows the risk-control signal is gone — otherwise always treated
        as unresolved,
        maintaining the safe default of "stop immediately". Callback is not invoked in dry-run (demo mode should not produce real
        side effects).
        """
        if not self.on_captcha or self.dry_run:
            return False
        log.warning("Detected captcha/risk control → handing to on_captcha callback (Mirage does not solve captchas)")
        try:
            res = self.on_captcha(self.page)
            if inspect.isawaitable(res):
                res = await res
        except Exception as e:                       # callback is user code, errors should not crash the main loop
            log.warning(f"on_captcha callback raised error, treating as unresolved: {e}")
            return False
        if not res:
            return False
        # Human-like refill timing: a real person looks around before acting after solving a captcha; **instant resume is itself a machine
        # trait**
        await human_sleep(4.0, 0.8, 2.0)
        if await self._danger():
            log.warning("Callback claims handled, but risk-control signal still present → not continuing")
            return False
        log.info("Captcha handled by callback, continuing after human-like pause")
        return True

    async def _visible_cards(self):
        """Identify note cards in the current viewport (multiple fallbacks, using current platform selectors)."""
        for sel in self.actor._selectors.get("note_card", []):
            try:
                loc = self.page.locator(sel)
                n = await loc.count()
                if n:
                    return [loc.nth(i) for i in range(min(n, 12))]
            except Exception:
                continue
        return []

    async def _decide_and_act(self, card):
        """For a note: mostly just browse; even opened notes are not necessarily interacted with (real people often swipe away after reading)."""
        # First decision: interaction tendency modulated by this round's "mood"; the vast majority just swipe past
        if random.random() > self.interact_prob * getattr(self, "_mood", 1.0):
            return False
        # Open the detail page, dwell to read (long tail: mostly 2.5~6s, occasionally much longer 8~20s)
        try:
            await self.actor._human_click(card, "note card")
            dwell = random.uniform(2.5, 6.0) if random.random() > 0.2 else random.uniform(8.0, 20.0)
            await asyncio.sleep(dwell)
        except Exception:
            pass
        acted = False
        # Second decision: "like only after truly reading enough" — only about 45% feel worth interacting after reading;
        # save the limited daily quota for quality content truly worth interacting with (precision > frequency)
        if random.random() < 0.45:
            roll = random.random()
            if roll < 0.70:
                acted = await self.actor.like_note()      # likes are the majority
            elif roll < 0.90:
                acted = await self.actor.collect_note()
            else:
                acted = await self.actor.follow_user()    # follow is the most sensitive → least frequent
        # Return to feed after reading
        try:
            await self.page.go_back()
            await human_sleep(1.0, 0.6, 1.4)
        except Exception:
            pass
        return acted

    async def run(self):
        log.info(f"=== Mirage account warming loop started ({'DRY-RUN demo' if self.dry_run else 'real interaction'}) ===")
        if not self.dry_run:
            log.warning("Real interaction mode: will actually like/follow people. Make sure you are using an alt account!")
        await warmup()
        start = time.time()
        rounds = 0
        while True:
            # —— Circuit breaker: highest priority ——
            if await self._danger():
                if self.radar:
                    self.radar.observe(ok=False, captcha=True)   # feed the radar for next trend judgement
                if await self._handle_captcha():
                    continue                                     # callback handled and signal gone, continue
                log.warning("Detected risk-control signal (captcha/rate-limit/abnormal), stopping immediately")
                break
            if self.policy.exhausted():
                log.info("Today's interaction budget fully used, done for the day")
                break
            if time.time() - start > self.max_seconds:
                log.info("Reached runtime limit, done")
                break

            # —— Time-slot awareness: rest directly in the deep night ——
            slot_mult = self.policy.interact_prob_multiplier()
            if slot_mult == 0.0:
                # Deep night (platform time 2~6), real people are rare; pause and check later
                slot = self.policy.current_slot()
                log.info(f"Current platform time slot [{slot}], unsuitable for interaction, pausing 600s and re-checking")
                await asyncio.sleep(600)   # re-evaluate time slot after 10 minutes
                continue

            # —— Browsing: scroll + bezier mouse + reading dwell ——
            await simulate_page_activity(self.page)

            # This round's "mood": interest fluctuates, interaction probability varies between rounds (a real person is not a constant 15%)
            # Also multiplied by the time-slot coefficient: night/quiet periods lower interaction willingness
            self._mood = random.uniform(0.5, 1.6) * slot_mult

            # —— Process random 2~4 notes; re-identify each time (avoid stale references after go_back) ——
            for _ in range(random.randint(2, 4)):
                if await self._danger():
                    break
                cards = await self._visible_cards()
                if not cards:
                    break
                await self._decide_and_act(random.choice(cards))  # pick randomly, not a fixed order
                await human_sleep(4.0, 0.7, 1.6)    # natural gap between interactions/browsing

            rounds += 1
            log.info(f"Round {rounds} complete | slot[{self.policy.current_slot()}×{slot_mult:.1f}] | today {self.policy.summary()}")

            # —— Soft-ban early warning: detect downranking before being banned ——
            slow_factor = 1.0
            if self.radar:
                self.radar.observe(ok=True)         # this round finished without hitting risk control
                v = self.radar.assess()
                if v.should_stop():
                    log.warning(f"Soft-ban radar {v.level}({v.score}/100): {v.advice}")
                    break
                if v.should_slow_down():
                    slow_factor = 2.0 if v.level == "warning" else 1.5
                    log.warning(f"Soft-ban radar {v.level}({v.score}/100) → slowing down ×{slow_factor} from this round; {v.advice}")
                elif rounds % 5 == 0:
                    log.info(self.radar.summary())

            await human_sleep(6.0 * slow_factor, 0.7, 1.5)   # inter-round pause (auto-lengthened when radar alarms)

            # —— Occasionally "zone out" with a long pause (real people get distracted by other things) ——
            if random.random() < 0.15:
                pause = random.uniform(20, 90)
                log.debug(f"Zoned out {pause:.0f}s")
                await asyncio.sleep(pause)

        log.info(f"=== Finished: {rounds} rounds total, today {self.policy.summary()} ===")
