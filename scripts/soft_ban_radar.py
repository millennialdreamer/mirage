# -*- coding: utf-8 -*-
"""
soft_ban_radar.py — 软封杀早期预警雷达（Mirage 的"观测位"能力）。

## 为什么需要它

现有的 `mirage_loop._danger()` 是**验证码弹出来了才熔断**——那时账号已经被标记，是"事后"。
但平台在硬封之前，通常先**悄悄降权**（shadow ban）：还能用，只是验证码变多、返回内容缩水、
响应变慢、成功率慢慢掉。这些信号**单看每一次都不异常，只有看趋势才看得出来**。

雷达做的就是这件事：**在被封之前看出"正在被盯上"**，主动降速/换号，而不是等 403。

## 为什么是 Mirage 来做（而不是别人）

反检测浏览器只管指纹、代理商只管 IP、打码平台只管过码——**只有 Mirage 同时坐在
"注入了什么 + 发出去什么 + 回来什么"这三者的交汇处**，是全链路唯一能观测到这五个信号的位置。

## 五个前兆信号

| 信号 | 含义 | 为什么是前兆 |
|------|------|-------------|
| 验证码触发率 ↑ | 最近窗口里遇到验证码/滑块的比例 | 正常应该≈0；一旦非零就是已被怀疑 |
| 返回完整度 ↓ | 拿到的字段数 / 应有字段数 | **降权最典型的表现：能返回但返回缩水**（静默变脏） |
| 延迟分布漂移 | 最近中位延迟 / 基线中位延迟 | 被限速时响应会明显变慢 |
| 蜜罐命中 | 抓到/点到了隐藏元素 | **确凿证据**——真人看不见的元素只有机器人会碰 |
| 成功率下降斜率 | 基线成功率 − 最近成功率 | 慢性劣化的直接体现 |

## 诚实边界（重要）

- 这是**启发式趋势判断，不是精确判定**。它给的是"该不该降速"的建议，不是"你被封了"的结论。
- 样本不足（< `MIN_SAMPLES`）时**明确返回"数据不足"而不是瞎猜**——小样本下的趋势没有意义。
- 阈值是经验值，不同平台差异很大，用 `SoftBanRadar(thresholds=...)` 自行调。
- 它**不能替代**风控熔断（`_danger()`）；两者是"预警"和"急刹"的关系，都要有。

## 用法

    from soft_ban_radar import SoftBanRadar

    radar = SoftBanRadar()                       # 自动加载历史基线
    ...每次请求/互动后记一笔...
    radar.observe(ok=True, latency=1.3, completeness=0.95, captcha=False)

    v = radar.assess()
    if v.level in ("警戒", "危险"):
        print(v.advice)                          # 按建议降速或停手
"""
from __future__ import annotations

import json
import os
import statistics
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

# 窗口与样本量
RECENT_WINDOW = 20        # "最近"取多少次
BASELINE_WINDOW = 60      # 基线最多回溯多少次（更早的丢弃，避免陈年数据拖累）
MIN_SAMPLES = 12          # 少于这个样本量不给结论——小样本趋势没有意义
MIN_BASELINE = 8          # 基线至少要这么多次才可比

# 判定阈值（经验值，平台差异大，可通过构造参数覆盖）
DEFAULT_THRESHOLDS = {
    "captcha_rate_warn": 0.01,     # 最近窗口出现任何验证码就该警觉
    "captcha_rate_alert": 0.10,
    "completeness_drop_warn": 0.10,   # 完整度比基线掉 10%
    "completeness_drop_alert": 0.25,
    "latency_ratio_warn": 1.6,        # 中位延迟涨到基线 1.6 倍
    "latency_ratio_alert": 2.5,
    "success_drop_warn": 0.15,        # 成功率比基线掉 15 个百分点
    "success_drop_alert": 0.30,
}

# 各信号权重（蜜罐是确凿证据，单独给最高权重）
WEIGHTS = {"captcha": 26, "completeness": 24, "latency": 16, "success": 22, "honeypot": 12}


@dataclass
class Observation:
    """一次观测。latency/completeness 拿不到就传 None，雷达会跳过对应信号。"""
    ts: float
    ok: bool = True
    latency: Optional[float] = None        # 秒
    completeness: Optional[float] = None   # 0~1：实得字段 / 应有字段
    captcha: bool = False
    honeypot: bool = False


@dataclass
class Verdict:
    level: str                              # 数据不足 / 正常 / 观察 / 警戒 / 危险
    score: int                              # 0~100，越高越危险
    advice: str
    signals: dict = field(default_factory=dict)
    samples: int = 0

    def should_slow_down(self) -> bool:
        return self.level in ("观察", "警戒", "危险")

    def should_stop(self) -> bool:
        return self.level == "危险"


def _median(xs):
    vals = [x for x in xs if x is not None]
    return statistics.median(vals) if vals else None


def _grade(value, warn, alert):
    """把一个指标映射成 0~1 的严重度（未达 warn=0，达 alert=1，中间线性）。"""
    if value is None or value <= warn:
        return 0.0
    if value >= alert:
        return 1.0
    span = alert - warn
    return (value - warn) / span if span > 0 else 1.0


class SoftBanRadar:
    """软封杀早期预警：累积观测 → 比对基线 → 给风险等级和建议。"""

    def __init__(self, state_path: str = "~/.mirage/softban_radar.json",
                 thresholds: Optional[dict] = None, account: str = "default") -> None:
        self.path = os.path.expanduser(state_path)
        self.account = account                      # 多账号分别建基线，互不污染
        self.th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._obs: list[Observation] = []
        self._load()

    # ── 持久化：趋势判断依赖历史基线，必须跨 session ──────────────
    def _load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get(self.account, [])
            self._obs = [Observation(**o) for o in raw][-BASELINE_WINDOW:]
        except Exception:
            self._obs = []                          # 不存在/损坏 → 从零开始

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
            os.replace(tmp, self.path)              # 原子写
        except Exception:
            pass                                    # 记录失败绝不打断主流程

    # ── 观测 ────────────────────────────────────────────────
    def observe(self, ok: bool = True, latency: Optional[float] = None,
                completeness: Optional[float] = None, captcha: bool = False,
                honeypot: bool = False) -> None:
        """记一次观测。在每次请求 / 每轮互动之后调用。"""
        self._obs.append(Observation(ts=time.time(), ok=ok, latency=latency,
                                     completeness=completeness, captcha=captcha,
                                     honeypot=honeypot))
        self._obs = self._obs[-BASELINE_WINDOW:]
        self._save()

    # ── 判定 ────────────────────────────────────────────────
    def assess(self) -> Verdict:
        """比对"最近窗口"与"更早的基线"，输出风险等级 + 建议。"""
        n = len(self._obs)
        if n < MIN_SAMPLES:
            return Verdict(level="数据不足", score=0, samples=n,
                           advice=f"只有 {n} 次观测（需 ≥{MIN_SAMPLES}）。样本太少，趋势没有意义——先正常跑，别据此下结论。")

        recent = self._obs[-RECENT_WINDOW:]
        baseline = self._obs[:-RECENT_WINDOW] or self._obs[:max(1, n // 2)]

        sig: dict = {}
        sev: dict = {}

        # 1) 验证码触发率（正常应≈0）
        cap_rate = sum(1 for o in recent if o.captcha) / len(recent)
        sig["验证码触发率"] = round(cap_rate, 3)
        sev["captcha"] = _grade(cap_rate, self.th["captcha_rate_warn"], self.th["captcha_rate_alert"])

        # 2) 蜜罐命中（确凿证据，一次即满格）
        hp = sum(1 for o in recent if o.honeypot)
        sig["蜜罐命中"] = hp
        sev["honeypot"] = 1.0 if hp else 0.0

        can_compare = len(baseline) >= MIN_BASELINE

        # 3) 返回完整度下降（降权最典型：能返回但缩水）
        r_comp, b_comp = _median([o.completeness for o in recent]), _median([o.completeness for o in baseline])
        if can_compare and r_comp is not None and b_comp is not None:
            drop = b_comp - r_comp
            sig["完整度下降"] = round(drop, 3)
            sev["completeness"] = _grade(drop, self.th["completeness_drop_warn"], self.th["completeness_drop_alert"])
        else:
            sev["completeness"] = 0.0

        # 4) 延迟漂移（被限速会明显变慢）
        r_lat, b_lat = _median([o.latency for o in recent]), _median([o.latency for o in baseline])
        if can_compare and r_lat and b_lat and b_lat > 0:
            ratio = r_lat / b_lat
            sig["延迟倍数"] = round(ratio, 2)
            sev["latency"] = _grade(ratio, self.th["latency_ratio_warn"], self.th["latency_ratio_alert"])
        else:
            sev["latency"] = 0.0

        # 5) 成功率下降
        r_ok = sum(1 for o in recent if o.ok) / len(recent)
        sig["最近成功率"] = round(r_ok, 3)
        if can_compare:
            b_ok = sum(1 for o in baseline if o.ok) / len(baseline)
            drop = b_ok - r_ok
            sig["成功率下降"] = round(drop, 3)
            sev["success"] = _grade(drop, self.th["success_drop_warn"], self.th["success_drop_alert"])
        else:
            sev["success"] = 0.0

        score = int(round(sum(WEIGHTS[k] * sev.get(k, 0.0) for k in WEIGHTS)))
        # 蜜罐命中是**确凿证据**（真人看不见的元素只有自动化会碰），不能被其它信号的"正常"稀释。
        # 单靠加权它只值 12 分会落进"正常"区间——那就与本模块把它称作确凿证据自相矛盾了。
        if hp:
            score = max(score, 40)                  # 一次命中即直接进警戒区
        score = max(0, min(100, score))

        if score >= 60:
            level, advice = "危险", "多个前兆同时恶化，很可能已被降权。**立即停手**，换号/换 IP，冷却数小时后再说。"
        elif score >= 35:
            level, advice = "警戒", "已有明显劣化趋势。建议立刻降速（间隔翻倍）、缩小批量、暂停互动，观察是否回升。"
        elif score >= 15:
            level, advice = "观察", "出现轻微劣化苗头。建议适度放慢，密切观察下一个窗口。"
        else:
            level, advice = "正常", "未见软封杀迹象。保持当前节奏即可。"

        if hp:
            advice = f"⚠ 命中蜜罐 {hp} 次——隐藏元素只有自动化会碰，这是被识别的确凿证据。" + advice
        if not can_compare:
            advice += f"（注：基线仅 {len(baseline)} 次，完整度/延迟/成功率的趋势对比暂未启用）"

        return Verdict(level=level, score=score, advice=advice, signals=sig, samples=n)

    def summary(self) -> str:
        v = self.assess()
        parts = " | ".join(f"{k}={val}" for k, val in v.signals.items())
        return f"[软封杀雷达] {v.level}({v.score}/100) 样本{v.samples}  {parts}"

    def reset(self) -> None:
        """换号/换 IP 后调用：旧基线不再适用，清空重建。"""
        self._obs = []
        self._save()
