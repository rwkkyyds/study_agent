"""
demo3：prometheus_client 真实指标写法

这个文件使用真实的 prometheus-client 包，不做模拟降级。
如果运行失败，说明环境没有安装依赖，请先执行：
    python -m pip install prometheus-client

运行方式：
    python demo3_prometheus_client_real.py
"""

from __future__ import annotations

import logging
import random
import time

from prometheus_client import Counter, Gauge, Histogram, generate_latest


logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


request_total = Counter(
    "demo_requests_total",
    "Total demo requests.",
    ["endpoint", "status"],
)  # 【Counter】累计值，只增不减，适合请求总数、错误总数。

active_users = Gauge(
    "demo_active_users",
    "Current active users.",
)  # 【Gauge】当前值，可增可减，适合在线人数、队列长度。

request_duration = Histogram(
    "demo_request_duration_seconds",
    "Demo request duration.",
    ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
)  # 【Histogram】分桶统计耗时，适合接口延迟、模型调用耗时。


def handle_chat_request(index: int) -> None:
    endpoint = "/chat"
    status = "200" if random.random() > 0.2 else "500"

    start = time.perf_counter()
    time.sleep(random.uniform(0.02, 0.12))  # 模拟真实接口处理耗时。
    cost_seconds = time.perf_counter() - start

    request_total.labels(endpoint=endpoint, status=status).inc()
    active_users.set(random.randint(1, 30))
    request_duration.labels(endpoint=endpoint).observe(cost_seconds)

    logger.info("第 %s 次请求：status=%s cost=%.3fs", index, status, cost_seconds)


def run_local_demo() -> None:
    for index in range(1, 4):
        handle_chat_request(index)

    print("\n=== prometheus_client Real Metrics Demo ===")
    print(generate_latest().decode("utf-8"))
    print("观察重点：这是真实 prometheus-client 生成的标准指标文本。")


if __name__ == "__main__":
    run_local_demo()

