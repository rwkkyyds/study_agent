"""不依赖第三方包的 Prometheus 文本指标采集器。"""

from __future__ import annotations

from collections import Counter
from threading import Lock


class Metrics:
    """收集客服请求总数、状态码和意图分布。"""

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests = 0
        self._rate_limited = 0
        self._statuses: Counter[int] = Counter()
        self._intents: Counter[str] = Counter()

    def record_request(self, status_code: int, intent: str | None = None) -> None:
        with self._lock:
            self._requests += 1
            self._statuses[status_code] += 1
            if status_code == 429:
                self._rate_limited += 1
            if intent:
                self._intents[intent] += 1

    def render(self) -> str:
        with self._lock:
            lines = [
                "# HELP customer_service_requests_total 客服请求总数",
                "# TYPE customer_service_requests_total counter",
                f"customer_service_requests_total {self._requests}",
                "# HELP customer_service_rate_limited_total 被限流的请求总数",
                "# TYPE customer_service_rate_limited_total counter",
                f"customer_service_rate_limited_total {self._rate_limited}",
                "# HELP customer_service_http_responses_total HTTP 状态码计数",
                "# TYPE customer_service_http_responses_total counter",
            ]
            lines.extend(
                f'customer_service_http_responses_total{{status_code="{code}"}} {count}'
                for code, count in sorted(self._statuses.items())
            )
            lines.extend([
                "# HELP customer_service_intents_total 客服意图计数",
                "# TYPE customer_service_intents_total counter",
            ])
            lines.extend(
                f'customer_service_intents_total{{intent="{intent}"}} {count}'
                for intent, count in sorted(self._intents.items())
            )
            return "\n".join(lines) + "\n"
