"""
demo1: FastAPI + prometheus_client 暴露真实 /metrics

这个 demo 是 Grafana 章节的“被监控服务”。
它负责产生 Prometheus 能抓取的指标，Grafana 后面只负责把这些指标画成图。

运行方式：
    uvicorn demo1_fastapi_metrics_app:app --reload --port 8000

观察地址：
    http://127.0.0.1:8000/metrics
"""

from __future__ import annotations

import random
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from prometheus_client import Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field


app = FastAPI(title="Grafana Learning Metrics App")


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=200)


http_requests_total = Counter(
    "demo_http_requests_total",
    "Total HTTP requests handled by the demo app.",
    ["method", "path", "status"],
)  # Counter：只增不减，适合统计请求总数、错误总数。

http_request_duration = Histogram(
    "demo_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)  # Histogram：把耗时放进不同区间，Grafana 常用它算 P95/P99。

active_users = Gauge(
    "demo_active_users",
    "Current active users in the demo app.",
)  # Gauge：当前值，可以变大也可以变小，适合在线人数、队列长度。


@app.middleware("http")
async def metrics_middleware(request: Request, call_next) -> Response:
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        cost_seconds = time.perf_counter() - start
        http_requests_total.labels(request.method, request.url.path, "500").inc()
        http_request_duration.labels(request.method, request.url.path).observe(cost_seconds)
        raise

    cost_seconds = time.perf_counter() - start
    http_requests_total.labels(
        request.method,
        request.url.path,
        str(response.status_code),
    ).inc()
    http_request_duration.labels(request.method, request.url.path).observe(cost_seconds)
    active_users.set(random.randint(1, 50))
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    time.sleep(random.uniform(0.03, 0.2))  # 模拟真实业务耗时，否则 Grafana 的耗时图太平。
    return {"reply": f"收到：{request.message}"}


@app.get("/boom")
def boom() -> dict[str, str]:
    time.sleep(random.uniform(0.02, 0.08))
    raise HTTPException(status_code=500, detail="模拟服务错误")


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

