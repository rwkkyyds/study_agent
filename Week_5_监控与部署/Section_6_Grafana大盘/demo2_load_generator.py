"""
demo2: 给 FastAPI 服务制造流量

Grafana 不是魔法，它只能展示已经存在的数据。
如果服务没人访问，Prometheus 抓到的指标也很少，Grafana 图表就会很空。

运行前请先启动：
    uvicorn demo1_fastapi_metrics_app:app --reload --port 8000

然后运行：
    python demo2_load_generator.py
"""

from __future__ import annotations

import random
import time

import requests


BASE_URL = "http://127.0.0.1:8000"


def call_health() -> int:
    response = requests.get(f"{BASE_URL}/health", timeout=3)
    return response.status_code


def call_chat() -> int:
    payload = {"message": random.choice(["hello", "grafana", "prometheus", "agent monitor"])}
    response = requests.post(f"{BASE_URL}/chat", json=payload, timeout=3)
    return response.status_code


def call_boom() -> int:
    response = requests.get(f"{BASE_URL}/boom", timeout=3)
    return response.status_code


def run() -> None:
    actions = [call_health, call_chat, call_chat, call_chat, call_boom]

    print("开始制造请求。按 Ctrl+C 停止。")
    print("观察 Grafana 大盘时，重点看请求量、5xx 错误、P95 耗时。")

    index = 1
    while True:
        action = random.choice(actions)
        try:
            status_code = action()
            print(f"第 {index} 次请求：{action.__name__} -> HTTP {status_code}")
        except requests.RequestException as exc:
            print(f"第 {index} 次请求失败：{exc}")

        index += 1
        time.sleep(random.uniform(0.2, 0.8))


if __name__ == "__main__":
    run()

