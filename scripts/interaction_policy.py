# -*- coding: utf-8 -*-
"""
interaction_policy.py — Mirage 互动节奏/配额层（"0 封控"的硬约束所在）。

三个机制：
  1. **保守每日上限**：默认值刻意低于风控线（宁可慢）；新号可砍到 1/3。
  2. **两次同类互动的最小间隔**：杜绝"秒赞""规律间隔"这类机器特征。
  3. **跨 session 计数持久化**：存到 ~/.mirage/interaction_state.json，
     **重启程序也不清零**（否则重启就能绕过上限），跨天才自动归零。

数字基于对小红书风控的保守认知（刷量/秒赞/批量关注是高危区），属经验取值，
用户可按自己号的情况调低；绝不建议调高。
"""

import json
import os
import time
from datetime import date, datetime

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo  # 3.8 回退包（pip install backports.zoneinfo）

# 每日上限（保守；真人重度用户的零头，给足安全垫）
DEFAULT_LIMITS = {"like": 150, "follow": 30, "collect": 80, "comment": 20}
# 两次同类互动的最小间隔（秒）——防秒赞/规律节奏
MIN_GAP = {"like": 25, "follow": 120, "collect": 40, "comment": 180}


# 时段定义（本地小时 → 场景）。深夜低谷：2~6 点；高峰：7~9、12~14、18~23
_TIME_SLOTS = {
    "deep_night": range(2, 6),   # 2:00~5:59 深夜：几乎没真人，强烈不建议互动
    "night":      range(0, 2),   # 0:00~1:59 后半夜：低流量
    "morning":    range(6, 12),  # 6:00~11:59 早晨/上午高峰
    "noon":       range(12, 15), # 12:00~14:59 午间高峰
    "afternoon":  range(15, 18), # 15:00~17:59 下午平稳
    "evening":    range(18, 24), # 18:00~23:59 晚间黄金高峰
}


class Policy:
    def __init__(self, state_path="~/.mirage/interaction_state.json",
                 limits=None, conservative=False,
                 platform_tz="Asia/Shanghai"):
        """
        platform_tz — 目标平台所在时区（IANA 名称）。
            默认 "Asia/Shanghai"（小红书等国内平台）。
            海外用户（如东京）操作国内平台时，依然应该填 "Asia/Shanghai"，
            因为判断的是"平台用户活跃时段"，而非操作者本地时间。
        """
        self.path = os.path.expanduser(state_path)
        self.limits = dict(limits or DEFAULT_LIMITS)
        if conservative:                         # 新号/冷启动期：上限砍到 1/3
            self.limits = {k: max(1, v // 3) for k, v in self.limits.items()}
        self._counts, self._last = {}, {}
        self._date = str(date.today())
        self._platform_tz = ZoneInfo(platform_tz)
        self._load()

    def _load(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
            if d.get("date") == self._date:      # 仅同一天继承计数；跨天自动归零
                self._counts = d.get("counts", {})
                self._last = d.get("last", {})
        except Exception:
            pass                                 # 不存在/损坏 → 当天从零开始

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"date": self._date, "counts": self._counts, "last": self._last}, f)
        os.replace(tmp, self.path)               # 原子写，防中断损坏

    def can(self, action):
        """今日未超限 且 距上次该动作已过最小间隔 才允许。"""
        if self._counts.get(action, 0) >= self.limits.get(action, 0):
            return False
        return (time.time() - self._last.get(action, 0)) >= MIN_GAP.get(action, 0)

    def record(self, action):
        """确认互动生效后才调用：计数 +1、记时间戳、立即持久化。"""
        self._counts[action] = self._counts.get(action, 0) + 1
        self._last[action] = time.time()
        self._save()

    def remaining(self):
        return {k: self.limits[k] - self._counts.get(k, 0) for k in self.limits}

    def exhausted(self):
        """所有动作都到顶了 → loop 该收工。"""
        return all(self._counts.get(k, 0) >= self.limits[k] for k in self.limits)

    def summary(self):
        return " | ".join(f"{k} {self._counts.get(k,0)}/{self.limits[k]}" for k in self.limits)

    # ── 时段感知：判断当前是否适合互动 ──────────────────────────────

    def current_slot(self) -> str:
        """返回平台时区下当前所属时段名称（deep_night/night/morning/noon/afternoon/evening）。"""
        now = datetime.now(tz=self._platform_tz)
        h = now.hour
        for slot, hrs in _TIME_SLOTS.items():
            if h in hrs:
                return slot
        return "evening"  # fallback

    def is_active_hour(self) -> bool:
        """
        判断当前时段是否适合互动。
        深夜（2~6 点平台时间）返回 False——这段时间真人极少，任何互动都很显眼。
        """
        return self.current_slot() != "deep_night"

    def interact_prob_multiplier(self) -> float:
        """
        根据时段返回 interact_prob 的缩放系数，供 mirage_loop 使用。
          - deep_night（2~6）：0.0（完全不互动，只浏览或直接歇）
          - night（0~2）：0.3（极低调）
          - morning/noon/evening 高峰：1.0（正常）
          - afternoon 平稳期：0.8（略降）
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
