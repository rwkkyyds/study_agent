"""
demo1：Prometheus 文本格式基础

这个文件不依赖 prometheus_client，先手动生成 /metrics 常见文本格式。
重点不是造轮子，而是让你看懂 Prometheus 到底抓取了什么。

运行方式：
    python demo1_metrics_plain_text.py
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import random
import time


logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class AppMetrics:
    request_total: int = 0
    error_total: int = 0
    active_users: int = 0

    def record_request(self, success: bool) -> None:
        self.request_total += 1  # 【Counter】请求总数只能增加，不能减少。
        if not success:
            self.error_total += 1  # 【Counter】错误总数也只能增加。

    def set_active_users(self, value: int) -> None:
        self.active_users = value  # 【Gauge】当前在线用户数可增可减。

    def render_prometheus_text(self) -> str:
        # Prometheus 文本格式由 HELP、TYPE 和具体指标值组成。
        return "\n".join(
            [
                "# HELP app_request_total Total number of handled requests.",
                "# TYPE app_request_total counter",
                f"app_request_total {self.request_total}",
                "# HELP app_error_total Total number of failed requests.",
                "# TYPE app_error_total counter",
                f"app_error_total {self.error_total}",
                "# HELP app_active_users Current active users.",
                "# TYPE app_active_users gauge",
                f"app_active_users {self.active_users}",
                "",
            ]
        )


def simulate_requests(metrics: AppMetrics) -> None:
    for index in range(1, 6):
        success = random.random() > 0.25
        metrics.record_request(success=success)
        metrics.set_active_users(random.randint(1, 20))
        logger.info("第 %s 次请求：success=%s", index, success)
        time.sleep(0.05)


def run_local_demo() -> None:
    metrics = AppMetrics()
    simulate_requests(metrics)

    print("\n=== Prometheus Plain Text Demo ===")
    print(metrics.render_prometheus_text())
    print("观察重点：Counter 适合累计次数，Gauge 适合当前状态。")


if __name__ == "__main__":
    run_local_demo()

