"""用标准库演示 Prometheus 指标文本格式和 Counter/Histogram 基础。"""

from __future__ import annotations

import time


class Metrics:
    """保存少量内存指标，并导出 Prometheus text exposition format。"""

    def __init__(self) -> None:
        self.requests_total = 0
        self.errors_total = 0
        self.duration_seconds: list[float] = []

    def observe_request(self, duration_seconds: float, error: bool = False) -> None:
        """记录一次请求及其耗时；error=True 时同时累加错误数。"""
        self.requests_total += 1
        self.duration_seconds.append(duration_seconds)
        if error:
            self.errors_total += 1

    def render(self) -> str:
        """输出 Prometheus 可抓取的指标文本。"""
        total = sum(self.duration_seconds)
        count = len(self.duration_seconds)
        lines = [
            "# HELP agent_requests_total Total agent requests.",
            "# TYPE agent_requests_total counter",
            f"agent_requests_total {self.requests_total}",
            "# HELP agent_errors_total Total agent errors.",
            "# TYPE agent_errors_total counter",
            f"agent_errors_total {self.errors_total}",
            "# HELP agent_request_duration_seconds Request duration summary.",
            "# TYPE agent_request_duration_seconds summary",
            f"agent_request_duration_seconds_sum {total:.6f}",
            f"agent_request_duration_seconds_count {count}",
        ]
        return "\n".join(lines) + "\n"


def main() -> None:
    metrics = Metrics()
    for duration, error in ((0.020, False), (0.080, False), (0.150, True)):
        time.sleep(0.01)
        metrics.observe_request(duration, error)
    print(metrics.render(), end="")


if __name__ == "__main__":
    main()

