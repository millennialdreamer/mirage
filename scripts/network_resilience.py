# -*- coding: utf-8 -*-
"""
network_resilience.py — Mirage network resilience layer.

Provides three capabilities:
  1. **Proxy rotation**: take turns from a list, mark failures with cooldown,
     trigger an alert when all fail instead of crashing.
  2. **Request retry**: exponential backoff + random jitter; distinguish
     retryable network errors from business errors (no retry).
  3. **Weak network / timeout circuit breaker**: consecutive failures exceed
     threshold -> enter open state, reject subsequent requests, wait for recovery.

Design principles:
  - Pure standard library (asyncio/time/random/dataclasses etc.), no extra dependencies.
  - async-friendly: all blocking waits use asyncio.sleep, can seamlessly cooperate
    with playwright/httpx.
  - dry-run friendly: ProxyPool.demo() demonstrates rotation + cooldown logic
    without actually connecting.
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
# 1. Proxy pool and rotator
# ─────────────────────────────────────────────────────────────────

@dataclasses.dataclass
class ProxyEntry:
    url: str                          # e.g. "http://user:pass@host:port"
    fail_count: int = 0               # cumulative failures this run
    cooldown_until: float = 0.0       # cooldown release timestamp (0 = not cooling)

    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

    def mark_fail(self, cooldown_secs: float = 120.0):
        """Mark failure and enter cooldown (default 2 minutes)."""
        self.fail_count += 1
        self.cooldown_until = time.time() + cooldown_secs
        logger.warning("Proxy failed: %s (cooldown %.0fs, cumulative failures %d)",
                       self.url, cooldown_secs, self.fail_count)

    def mark_ok(self):
        """On success clear failure record and lift cooldown."""
        self.fail_count = 0
        self.cooldown_until = 0.0


class ProxyPool:
    """
    Rotating proxy pool.

    Usage::

        pool = ProxyPool(["http://p1:1080", "http://p2:1080"])
        proxy = pool.next()          # get next available proxy, None if all down
        pool.mark_fail(proxy)
        pool.mark_ok(proxy)
    """

    def __init__(self, proxy_urls: List[str], cooldown_secs: float = 120.0):
        self.entries = [ProxyEntry(u) for u in proxy_urls]
        self.cooldown_secs = cooldown_secs
        self._idx = 0                 # round-robin cursor

    def next(self) -> Optional[str]:
        """
        Return the next available proxy URL, or None (all cooling down / list empty).
        Uses round-robin to skip cooling proxies.
        """
        if not self.entries:
            return None
        n = len(self.entries)
        for _ in range(n):
            entry = self.entries[self._idx % n]
            self._idx += 1
            if entry.is_available():
                return entry.url
        # all cooling down
        logger.error("Proxy pool exhausted: all %d proxies are cooling down; no proxy available", n)
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
            state = f"cooldown remaining {cd:.0f}s" if cd > 0 else "available"
            lines.append(f"  {e.url}  [{state}, failures {e.fail_count}]")
        return "\n".join(lines) or "(no proxy)"

    @classmethod
    def demo(cls):
        """Demonstrate rotation + cooldown logic without real network access."""
        print("=== ProxyPool demo ===")
        pool = cls(["http://p1:1080", "http://p2:1080", "http://p3:1080"],
                   cooldown_secs=5.0)
        # take in sequence
        for i in range(5):
            p = pool.next()
            print(f"  attempt {i+1}: {p}")
        # mark p1 and p2 as failed
        pool.mark_fail("http://p1:1080")
        pool.mark_fail("http://p2:1080")
        print("After marking p1/p2 as failed:")
        print(pool.status())
        p = pool.next()
        print(f"  now got: {p}")  # should be p3
        print("=== demo end ===")


# ─────────────────────────────────────────────────────────────────
# 2. Retryable vs non-retryable error classification
# ─────────────────────────────────────────────────────────────────

class RetryPolicy(Enum):
    RETRYABLE = "retryable"        # network-layer error, retryable (timeout/connection reset/503 etc.)
    NOT_RETRYABLE = "not_retryable"  # business-layer error, retry won't help (4xx/content issues etc.)


# Map common exception keywords to policy (string matching, compatible with
# playwright/httpx/requests exceptions)
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
    """Determine whether the error is retryable based on exception type / message."""
    msg = str(exc).lower()
    if any(p in msg for p in _NOT_RETRYABLE_PATTERNS):
        return RetryPolicy.NOT_RETRYABLE
    if any(p in msg for p in _RETRYABLE_PATTERNS):
        return RetryPolicy.RETRYABLE
    return RetryPolicy.RETRYABLE  # unknown errors conservatively treated as retryable


# ─────────────────────────────────────────────────────────────────
# 3. Exponential backoff retry (async)
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
    Exponential backoff + random jitter retry wrapper.

    Args:
        fn           — async callable target
        max_retries  — maximum retry count (excluding the first attempt)
        base_delay   — first wait seconds (doubles each time)
        max_delay    — maximum single wait seconds
        jitter       — random jitter ratio applied to backoff (0.3 = ±30%)
        on_retry     — callback before each retry (receives attempt, exc, delay)

    Retryable error → wait then retry; non-retryable error → raise immediately.
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            policy = classify_error(exc)
            if policy == RetryPolicy.NOT_RETRYABLE:
                logger.warning("Non-retryable error (business layer), giving up: %s", exc)
                raise
            last_exc = exc
            if attempt >= max_retries:
                break
            # exponential backoff + jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay *= random.uniform(1 - jitter, 1 + jitter)
            logger.info("Network error (retry %d/%d, waiting %.1fs): %s",
                        attempt + 1, max_retries, delay, exc)
            if on_retry:
                on_retry(attempt + 1, exc, delay)
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore


# ─────────────────────────────────────────────────────────────────
# 4. Weak network circuit breaker
# ─────────────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"        # normal traffic
    OPEN = "open"            # open, rejecting requests
    HALF_OPEN = "half_open"  # probing recovery


class CircuitBreakerOpen(Exception):
    """Raised when the circuit breaker is open; callers should immediately stop the current session."""


class CircuitBreaker:
    """
    Simple three-state circuit breaker.

    Consecutive failures reach failure_threshold -> enter OPEN (tripped),
    after recovery_secs enter HALF_OPEN (probe),
    probe succeeds -> CLOSED, probe fails -> re-OPEN.

    Usage::

        cb = CircuitBreaker()
        try:
            async with cb:
                await do_request()
        except CircuitBreakerOpen:
            print("circuit open, stop sending requests")
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
                logger.info("Circuit breaker recovery probe period (HALF_OPEN)")
        return self._state

    async def __aenter__(self):
        s = self.state
        if s == CircuitState.OPEN:
            raise CircuitBreakerOpen(
                f"Network circuit breaker open (failed {self.failure_threshold} consecutive times), "
                f"waiting {self.recovery_secs:.0f}s before automatic recovery probe"
            )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is None:
            # success
            self._fail_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info("Probe succeeded, circuit breaker closed (CLOSED)")
        elif exc_type is not CircuitBreakerOpen:
            # failure
            self._fail_count += 1
            logger.warning("Circuit breaker count %d/%d, error: %s",
                           self._fail_count, self.failure_threshold, exc)
            if self._fail_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                logger.error("🛑 Circuit breaker tripped! %d consecutive failures, entering OPEN state, "
                             "probing recovery in %.0fs", self._fail_count, self.recovery_secs)
        return False  # do not swallow exceptions; let the caller handle them

    def status(self) -> str:
        s = self.state
        if s == CircuitState.OPEN:
            remaining = self.recovery_secs - (time.time() - self._opened_at)
            return f"OPEN (cooldown remaining {remaining:.0f}s, failure count {self._fail_count})"
        return f"{s.value} (failure count {self._fail_count}/{self.failure_threshold})"


# ─────────────────────────────────────────────────────────────────
# 5. Convenience demo entry (no real network)
# ─────────────────────────────────────────────────────────────────

async def _demo_retry():
    """Demo: retry logic (fails every time, observe backoff timing)."""
    print("\n=== retry_async demo (exponential backoff, max_retries=3) ===")
    call_times = []

    async def always_fail():
        call_times.append(time.time())
        raise ConnectionError("simulated network timeout")

    try:
        await retry_async(always_fail, max_retries=3, base_delay=0.5,
                          on_retry=lambda n, e, d: print(f"  → retry #{n}, waiting {d:.2f}s"))
    except ConnectionError as e:
        print(f"  final failure: {e}")
    gaps = [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]
    print(f"  actual wait intervals (seconds): {[f'{g:.2f}' for g in gaps]}")
    print("=== demo end ===")


async def _demo_circuit_breaker():
    """Demo: circuit breaker trip and recovery."""
    print("\n=== CircuitBreaker demo (threshold=3) ===")
    cb = CircuitBreaker(failure_threshold=3, recovery_secs=3.0)

    async def fail_request():
        raise ConnectionError("simulated network disconnected")

    for i in range(5):
        try:
            async with cb:
                await fail_request()
        except CircuitBreakerOpen as e:
            print(f"  attempt {i+1}: rejected by circuit breaker → {e}")
            break
        except ConnectionError:
            print(f"  attempt {i+1}: failure | status: {cb.status()}")

    print("  waiting 3s to enter HALF_OPEN automatically…")
    await asyncio.sleep(3.1)
    print(f"  current status: {cb.status()}")
    print("=== demo end ===")


async def demo():
    """Run all demos at once (dry-run, no real network)."""
    ProxyPool.demo()
    await _demo_retry()
    await _demo_circuit_breaker()


if __name__ == "__main__":
    asyncio.run(demo())
