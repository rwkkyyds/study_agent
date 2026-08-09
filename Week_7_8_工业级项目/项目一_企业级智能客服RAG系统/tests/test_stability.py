"""阶段五稳定性组件测试。"""

import pytest

from app.stability.memory import SessionMemory
from app.stability.metrics import Metrics
from app.stability.rate_limit import SlidingWindowRateLimiter
from app.stability.resilience import CircuitBreaker, CircuitOpenError, call_with_retry


def test_rate_limiter_rejects_after_limit():
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("user-1") is True
    assert limiter.allow("user-1") is True
    assert limiter.allow("user-1") is False
    assert limiter.allow("user-2") is True


def test_session_memory_keeps_recent_messages():
    memory = SessionMemory(max_messages=2)
    memory.append(1, "user", "第一条")
    memory.append(1, "assistant", "第二条")
    memory.append(1, "user", "第三条")

    assert [item["content"] for item in memory.recent(1)] == ["第二条", "第三条"]


def test_session_memory_rejects_blank_content():
    with pytest.raises(ValueError):
        SessionMemory().append(1, "user", " ")


def test_metrics_render_prometheus_text():
    metrics = Metrics()
    metrics.record_request(200, "knowledge")
    metrics.record_request(429)

    rendered = metrics.render()

    assert "customer_service_requests_total 2" in rendered
    assert 'customer_service_intents_total{intent="knowledge"} 1' in rendered
    assert "customer_service_rate_limited_total 1" in rendered


def test_call_with_retry_retries_then_succeeds():
    attempts = []

    def operation():
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("temporary")
        return "ok"

    assert call_with_retry(operation, retries=2, backoff_seconds=0) == "ok"
    assert len(attempts) == 3


def test_circuit_breaker_opens_after_failures():
    breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=60)

    for _ in range(2):
        with pytest.raises(RuntimeError):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("down")))

    with pytest.raises(CircuitOpenError):
        breaker.call(lambda: "should not run")
