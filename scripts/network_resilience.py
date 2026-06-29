# -*- coding: utf-8 -*-
"""
network_resilience.py — Mirage 网络容错层。

提供三个能力：
  1. **代理轮换**：从列表轮流取，失败标记冷却，全挂了触发告警而非崩溃。
  2. **请求重试**：指数退避 + 随机抖动；区分「可重试网络错误」和「业务错误(不重试)」。
  3. **弱网/超时熔断**：连续失败超阈值 → 进入熔断状态，拒绝后续请求，等待恢复。

设计原则：
  - 纯标准库（asyncio/time/random/dataclasses 等），无额外依赖。
  - async 友好：所有阻塞等待走 asyncio.sleep，可无缝配合 playwright/httpx。
  - dry-run 友好：ProxyPool.demo() 不真连网就能演示轮换 + 冷却逻辑。
"""

import asyncio
import dataclasses
import logging
import random
import time
from enum import Enum
from typing import Callable, List, Optional

logger = logging.getLogger("mirage.network")

# ─────────────────────────────────────────────────────────────────
# 1. 代理池与轮换器
# ─────────────────────────────────────────────────────────────────

@dataclasses.dataclass
class ProxyEntry:
    url: str                          # 形如 "http://user:pass@host:port"
    fail_count: int = 0               # 本次运行累计失败次数
    cooldown_until: float = 0.0       # 冷却解除时间戳（0 = 未冷却）

    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

    def mark_fail(self, cooldown_secs: float = 120.0):
        """标记失败并进入冷却期（默认 2 分钟）。"""
        self.fail_count += 1
        self.cooldown_until = time.time() + cooldown_secs
        logger.warning("代理失败：%s（冷却 %.0fs，累计失败 %d 次）",
                       self.url, cooldown_secs, self.fail_count)

    def mark_ok(self):
        """成功后清零失败记录，解除冷却。"""
        self.fail_count = 0
        self.cooldown_until = 0.0


class ProxyPool:
    """
    轮换式代理池。

    用法::

        pool = ProxyPool(["http://p1:1080", "http://p2:1080"])
        proxy = pool.next()          # 取下一个可用代理，全挂了返回 None
        pool.mark_fail(proxy)
        pool.mark_ok(proxy)
    """

    def __init__(self, proxy_urls: List[str], cooldown_secs: float = 120.0):
        self.entries = [ProxyEntry(u) for u in proxy_urls]
        self.cooldown_secs = cooldown_secs
        self._idx = 0                 # 轮询游标

    def next(self) -> Optional[str]:
        """
        返回下一个可用代理 URL，或 None（全部在冷却/列表为空）。
        采用轮询（Round-Robin）跳过冷却中的代理。
        """
        if not self.entries:
            return None
        n = len(self.entries)
        for _ in range(n):
            entry = self.entries[self._idx % n]
            self._idx += 1
            if entry.is_available():
                return entry.url
        # 全部在冷却
        logger.error("代理池耗尽：所有 %d 个代理均在冷却，当前无可用代理", n)
        return None

    def mark_fail(self, url: str):
        for e in self.entries:
            if e.url == url:
                e.mark_fail(self.cooldown_secs)
                return

    def mark_ok(self, url: str):
        for e in self.entries:
            if e.url == url:
                e.mark_ok()
                return

    def status(self) -> str:
        lines = []
        for e in self.entries:
            cd = e.cooldown_until - time.time()
            state = f"冷却剩余 {cd:.0f}s" if cd > 0 else "可用"
            lines.append(f"  {e.url}  [{state}，失败 {e.fail_count} 次]")
        return "\n".join(lines) or "（无代理）"

    @classmethod
    def demo(cls):
        """不真连网，演示轮换 + 冷却逻辑。"""
        print("=== ProxyPool 演示 ===")
        pool = cls(["http://p1:1080", "http://p2:1080", "http://p3:1080"],
                   cooldown_secs=5.0)
        # 依次取
        for i in range(5):
            p = pool.next()
            print(f"  第{i+1}次取: {p}")
        # 让 p1、p2 失败
        pool.mark_fail("http://p1:1080")
        pool.mark_fail("http://p2:1080")
        print("标记 p1/p2 失败后：")
        print(pool.status())
        p = pool.next()
        print(f"  现在取到: {p}")  # 应该是 p3
        print("=== 演示结束 ===")


# ─────────────────────────────────────────────────────────────────
# 2. 可重试 vs 不可重试错误分类
# ─────────────────────────────────────────────────────────────────

class RetryPolicy(Enum):
    RETRYABLE = "retryable"        # 网络层错误，可重试（超时/连接断/503 等）
    NOT_RETRYABLE = "not_retryable"  # 业务层错误，重试也没用（4xx/内容异常等）


# 把常见异常关键词映射到策略（字符串匹配，兼容 playwright/httpx/requests 各类异常）
_RETRYABLE_PATTERNS = [
    "timeout", "timed out", "connection", "reset", "broken pipe",
    "eof", "503", "502", "429", "too many requests", "network", "unreachable",
    "ssl", "proxy", "connect", "refused",
]
_NOT_RETRYABLE_PATTERNS = [
    "400", "401", "403", "404", "content blocked", "business error",
    "login required", "验证码", "账号异常",
]


def classify_error(exc: Exception) -> RetryPolicy:
    """根据异常类型 / 错误信息判断是否可重试。"""
    msg = str(exc).lower()
    if any(p in msg for p in _NOT_RETRYABLE_PATTERNS):
        return RetryPolicy.NOT_RETRYABLE
    if any(p in msg for p in _RETRYABLE_PATTERNS):
        return RetryPolicy.RETRYABLE
    return RetryPolicy.RETRYABLE  # 未知错误保守当可重试


# ─────────────────────────────────────────────────────────────────
# 3. 指数退避重试（async）
# ─────────────────────────────────────────────────────────────────

async def retry_async(
    fn: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.5,
    max_delay: float = 60.0,
    jitter: float = 0.3,
    on_retry: Optional[Callable] = None,
    **kwargs,
):
    """
    指数退避 + 随机抖动重试包装。

    参数：
        fn           — async 可调用目标
        max_retries  — 最多重试次数（不含首次）
        base_delay   — 首次等待秒数（每次 ×2）
        max_delay    — 单次最长等待秒数
        jitter       — 在退避时间上叠加的随机抖动比例（0.3 = ±30%）
        on_retry     — 每次重试前的回调（接收 attempt, exc, delay）

    可重试错误 → 等待后重试；不可重试错误 → 立刻抛出。
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            policy = classify_error(exc)
            if policy == RetryPolicy.NOT_RETRYABLE:
                logger.warning("不可重试错误（业务层），直接放弃：%s", exc)
                raise
            last_exc = exc
            if attempt >= max_retries:
                break
            # 指数退避 + 抖动
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay *= random.uniform(1 - jitter, 1 + jitter)
            logger.info("网络错误（第 %d/%d 次重试，等待 %.1fs）：%s",
                        attempt + 1, max_retries, delay, exc)
            if on_retry:
                on_retry(attempt + 1, exc, delay)
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore


# ─────────────────────────────────────────────────────────────────
# 4. 弱网熔断器（Circuit Breaker）
# ─────────────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"        # 正常通行
    OPEN = "open"            # 熔断中，拒绝请求
    HALF_OPEN = "half_open"  # 试探恢复


class CircuitBreakerOpen(Exception):
    """熔断器打开时，外部调用方收到此异常，应立即停止当前 session。"""


class CircuitBreaker:
    """
    简单三态熔断器。

    连续失败 failure_threshold 次 → 进入 OPEN（熔断），
    等待 recovery_secs 后进入 HALF_OPEN（试探），
    试探成功 → CLOSED，试探失败 → 重新 OPEN。

    用法::

        cb = CircuitBreaker()
        try:
            async with cb:
                await do_request()
        except CircuitBreakerOpen:
            print("熔断中，停止发请求")
    """

    def __init__(self, failure_threshold: int = 5, recovery_secs: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_secs = recovery_secs
        self._state = CircuitState.CLOSED
        self._fail_count = 0
        self._opened_at: float = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._opened_at >= self.recovery_secs:
                self._state = CircuitState.HALF_OPEN
                logger.info("熔断恢复探测期（HALF_OPEN）")
        return self._state

    async def __aenter__(self):
        s = self.state
        if s == CircuitState.OPEN:
            raise CircuitBreakerOpen(
                f"网络熔断中（已连续失败 {self.failure_threshold} 次），"
                f"等待 {self.recovery_secs:.0f}s 后自动恢复探测"
            )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is None:
            # 成功
            self._fail_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info("探测成功，熔断器关闭（CLOSED）")
        elif exc_type is not CircuitBreakerOpen:
            # 失败
            self._fail_count += 1
            logger.warning("熔断器计数 %d/%d，错误：%s",
                           self._fail_count, self.failure_threshold, exc)
            if self._fail_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                logger.error("🛑 熔断器触发！连续失败 %d 次，进入 OPEN 状态，"
                             "%.0fs 后试探恢复", self._fail_count, self.recovery_secs)
        return False  # 不吞异常，让调用方自己处理

    def status(self) -> str:
        s = self.state
        if s == CircuitState.OPEN:
            remaining = self.recovery_secs - (time.time() - self._opened_at)
            return f"OPEN（剩余冷却 {remaining:.0f}s，失败计数 {self._fail_count}）"
        return f"{s.value}（失败计数 {self._fail_count}/{self.failure_threshold}）"


# ─────────────────────────────────────────────────────────────────
# 5. 便捷演示入口（不真连网）
# ─────────────────────────────────────────────────────────────────

async def _demo_retry():
    """演示：重试逻辑（每次都失败，看退避时序）。"""
    print("\n=== retry_async 演示（指数退避，max_retries=3）===")
    call_times = []

    async def always_fail():
        call_times.append(time.time())
        raise ConnectionError("模拟网络超时 timeout")

    try:
        await retry_async(always_fail, max_retries=3, base_delay=0.5,
                          on_retry=lambda n, e, d: print(f"  → 第{n}次重试，等待 {d:.2f}s"))
    except ConnectionError as e:
        print(f"  最终失败：{e}")
    gaps = [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]
    print(f"  实际等待间隔（秒）：{[f'{g:.2f}' for g in gaps]}")
    print("=== 演示结束 ===")


async def _demo_circuit_breaker():
    """演示：熔断器触发与恢复。"""
    print("\n=== CircuitBreaker 演示（threshold=3）===")
    cb = CircuitBreaker(failure_threshold=3, recovery_secs=3.0)

    async def fail_request():
        raise ConnectionError("模拟网络断开")

    for i in range(5):
        try:
            async with cb:
                await fail_request()
        except CircuitBreakerOpen as e:
            print(f"  第{i+1}次：熔断拒绝 → {e}")
            break
        except ConnectionError:
            print(f"  第{i+1}次：失败 | 状态：{cb.status()}")

    print("  等待 3s 后自动进入 HALF_OPEN…")
    await asyncio.sleep(3.1)
    print(f"  当前状态：{cb.status()}")
    print("=== 演示结束 ===")


async def demo():
    """一键运行所有演示（dry-run，不真连网）。"""
    ProxyPool.demo()
    await _demo_retry()
    await _demo_circuit_breaker()


if __name__ == "__main__":
    asyncio.run(demo())
