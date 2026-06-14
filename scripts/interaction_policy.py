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
from datetime import date

# 每日上限（保守；真人重度用户的零头，给足安全垫）
DEFAULT_LIMITS = {"like": 150, "follow": 30, "collect": 80, "comment": 20}
# 两次同类互动的最小间隔（秒）——防秒赞/规律节奏
MIN_GAP = {"like": 25, "follow": 120, "collect": 40, "comment": 180}


class Policy:
    def __init__(self, state_path="~/.mirage/interaction_state.json",
                 limits=None, conservative=False):
        self.path = os.path.expanduser(state_path)
        self.limits = dict(limits or DEFAULT_LIMITS)
        if conservative:                         # 新号/冷启动期：上限砍到 1/3
            self.limits = {k: max(1, v // 3) for k, v in self.limits.items()}
        self._counts, self._last = {}, {}
        self._date = str(date.today())
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
