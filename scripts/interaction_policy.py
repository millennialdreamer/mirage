# -*- coding: utf-8 -*-
"""
interaction_policy.py — Mirage interaction rhythm/quota layer (where the "0 risk control" hard constraints live).

Three mechanisms:
  1. **Conservative daily caps**: defaults are deliberately below the risk-control line (better slow); new accounts can be cut to 1/3.
  2. **Minimum interval between two interactions of the same type**: eliminates machine traits like "instant likes" and "regular intervals".
  3. **Cross-session counter persistence**: stored in ~/.mirage/interaction_state.json;
     **restarting the program does not reset it** (otherwise restarting would bypass the caps), and it only auto-resets across days.

The numbers are based on conservative understanding of Xiaohongshu risk control (mass liking/instant likes/batch follows are high-
risk areas); they are empirical values.
Users may lower them according to their own account status; raising them is never recommended.
"""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime
from typing import Optional

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo  # 3.8 fallback package (pip install backports.zoneinfo)

# Daily caps (conservative; a fraction of a heavy real user, giving ample safety margin)
DEFAULT_LIMITS = {"like": 150, "follow": 30, "collect": 80, "comment": 20}
# Minimum interval between two interactions of the same type (seconds) — prevents instant likes / regular rhythm
MIN_GAP = {"like": 25, "follow": 120, "collect": 40, "comment": 180}


# Time slot definitions (local hour -> scenario). Deep-night trough: 2~6; peaks: 7~9, 12~14, 18~23
_TIME_SLOTS = {
    "deep_night": range(2, 6),   # 2:00~5:59 deep night: almost no real users, strongly discouraged
    "night":      range(0, 2),   # 0:00~1:59 late night: low traffic
    "morning":    range(6, 12),  # 6:00~11:59 morning peak
    "noon":       range(12, 15), # 12:00~14:59 midday peak
    "afternoon":  range(15, 18), # 15:00~17:59 stable afternoon
    "evening":    range(18, 24), # 18:00~23:59 evening prime peak
}


class Policy:
    def __init__(self, state_path: str = "~/.mirage/interaction_state.json",
                 limits: Optional[dict[str, int]] = None, conservative: bool = False,
                 platform_tz: str = "Asia/Shanghai") -> None:
        """
        platform_tz — IANA time zone of the target platform.
            Default "Asia/Shanghai" (for domestic platforms like Xiaohongshu).
            Overseas users (e.g., Tokyo) operating a domestic platform should still use "Asia/Shanghai",
            because what matters is the "platform user active hours", not the operator's local time.
        """
        self.path = os.path.expanduser(state_path)
        self.limits = dict(limits or DEFAULT_LIMITS)
        if conservative:                         # new account / cold-start period: cut caps to 1/3
            self.limits = {k: max(1, v // 3) for k, v in self.limits.items()}
        self._counts: dict[str, int] = {}     # action -> today's count
        self._last: dict[str, float] = {}      # action -> last timestamp
        self._date = str(date.today())
        self._platform_tz = ZoneInfo(platform_tz)
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path) as f:
                d = json.load(f)
            if d.get("date") == self._date:      # only inherit counts for the same day; auto-reset across days
                self._counts = d.get("counts", {})
                self._last = d.get("last", {})
        except Exception:
            pass                                 # missing/corrupt -> start today from zero

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"date": self._date, "counts": self._counts, "last": self._last}, f)
        os.replace(tmp, self.path)               # atomic write, prevents corruption from interruption

    def can(self, action: str) -> bool:
        """Allowed only if today's cap is not exceeded and the minimum gap since the last same action has elapsed."""
        if self._counts.get(action, 0) >= self.limits.get(action, 0):
            return False
        return (time.time() - self._last.get(action, 0)) >= MIN_GAP.get(action, 0)

    def record(self, action: str) -> None:
        """Call only after confirming the interaction took effect: increment count, record timestamp, persist immediately."""
        self._counts[action] = self._counts.get(action, 0) + 1
        self._last[action] = time.time()
        self._save()

    def remaining(self) -> dict[str, int]:
        return {k: self.limits[k] - self._counts.get(k, 0) for k in self.limits}

    def exhausted(self) -> bool:
        """All actions are at cap -> the loop should call it a day."""
        return all(self._counts.get(k, 0) >= self.limits[k] for k in self.limits)

    def summary(self) -> str:
        return " | ".join(f"{k} {self._counts.get(k,0)}/{self.limits[k]}" for k in self.limits)

    # ── time-slot awareness: determine whether now is suitable for interacting ──────────────────────────────

    def current_slot(self) -> str:
        """Return the current slot name in the platform time zone (deep_night/night/morning/noon/afternoon/evening)."""
        now = datetime.now(tz=self._platform_tz)
        h = now.hour
        for slot, hrs in _TIME_SLOTS.items():
            if h in hrs:
                return slot
        return "evening"  # fallback

    def is_active_hour(self) -> bool:
        """
        Determine whether the current time slot is suitable for interacting.
        Deep night (2~6 a.m. platform time) returns False — during this period real users are extremely few, so any interaction is
        very conspicuous.
        """
        return self.current_slot() != "deep_night"

    def interact_prob_multiplier(self) -> float:
        """
        Return a scaling factor for interact_prob based on the time slot, for use by mirage_loop.
          - deep_night (2~6): 0.0 (no interaction at all, just browse or rest)
          - night (0~2): 0.3 (extremely low-key)
          - morning/noon/evening peak: 1.0 (normal)
          - afternoon stable period: 0.8 (slightly reduced)
        """
        slot = self.current_slot()
        return {
            "deep_night": 0.0,
            "night":      0.3,
            "morning":    1.0,
            "noon":       1.0,
            "afternoon":  0.8,
            "evening":    1.0,
        }.get(slot, 1.0)
