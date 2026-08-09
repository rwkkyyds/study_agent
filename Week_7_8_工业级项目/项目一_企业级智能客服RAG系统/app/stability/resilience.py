"""外部依赖调用的超时、重试和熔断基础设施。"""

from __future__ import annotations

import time
from threading import Lock
from typing import Callable, TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """熔断器打开时拒绝调用。"""


class CircuitBreaker:
    """连续失败达到阈值后临时熔断，冷却后允许半开探测。"""

    def __init__(self, failure_threshold: int = 3, recovery_seconds: float = 30.0) -> None:
        if failure_threshold <= 0 or recovery_seconds <= 0:
            raise ValueError("failure_threshold 和 recovery_seconds 必须大于 0")
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = Lock()

    def call(self, operation: Callable[[], T]) -> T:
        with self._lock:
            if self._opened_at is not None:
                if time.monotonic() - self._opened_at < self.recovery_seconds:
                    raise CircuitOpenError("外部服务暂时不可用")
                self._opened_at = None
        try:
            result = operation()
        except Exception:
            with self._lock:
                self._failures += 1
                if self._failures >= self.failure_threshold:
                    self._opened_at = time.monotonic()
            raise
        with self._lock:
            self._failures = 0
            self._opened_at = None
        return result


def call_with_retry(
    operation: Callable[[], T],
    *,
    retries: int = 2,
    timeout_seconds: float | None = None,
    backoff_seconds: float = 0.05,
    breaker: CircuitBreaker | None = None,
) -> T:
    """执行有限次数重试；超时使用线程不可安全中断，因此由调用方控制连接超时。"""

    if retries < 0 or backoff_seconds < 0:
        raise ValueError("retries 和 backoff_seconds 不能为负数")
    started = time.monotonic()
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        if timeout_seconds is not None and time.monotonic() - started >= timeout_seconds:
            raise TimeoutError("外部服务调用超时") from last_error
        try:
            if breaker is None:
                return operation()
            return breaker.call(operation)
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                raise
            time.sleep(backoff_seconds * (2**attempt))
    raise RuntimeError("重试执行异常")
