"""
demo2：FastAPI middleware 暴露 /metrics

这个文件演示：
1. 每次请求经过 middleware 时自动统计次数和耗时
2. /metrics 输出 Prometheus 可以读取的文本格式
3. 不依赖 prometheus_client，先理解指标本质

运行方式：
    python demo2_fastapi_metrics_middleware.py
"""

from __future__ import annotations

from collections import defaultdict
import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=200)


class MetricStore:
    def __init__(self) -> None:
        self.request_total: dict[tuple[str, str, int], int] = defaultdict(int)
        self.request_duration_buckets: dict[tuple[str, str, float], int] = defaultdict(int)
        self.error_total: dict[tuple[str, str], int] = defaultdict(int)
        self.buckets = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0]

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        cost_seconds: float,
    ) -> None:
        # 【label】method/path/status 用来区分不同接口和响应结果。
        self.request_total[(method, path, status_code)] += 1
        if status_code >= 500:
            self.error_total[(method, path)] += 1

        for bucket in self.buckets:
            if cost_seconds <= bucket:
                self.request_duration_buckets[(method, path, bucket)] += 1

    def render(self) -> str:
        lines = [
            "# HELP http_requests_total Total HTTP requests.",
            "# TYPE http_requests_total counter",
        ]

        for (method, path, status_code), value in sorted(self.request_total.items()):
            lines.append(
                f'http_requests_total{{method="{method}",path="{path}",status="{status_code}"}} {value}'
            )

        lines.extend(
            [
                "# HELP http_request_errors_total Total HTTP 5xx errors.",
                "# TYPE http_request_errors_total counter",
            ]
        )
        for (method, path), value in sorted(self.error_total.items()):
            lines.append(
                f'http_request_errors_total{{method="{method}",path="{path}"}} {value}'
            )

        lines.extend(
            [
                "# HELP http_request_duration_seconds_bucket HTTP request duration buckets.",
                "# TYPE http_request_duration_seconds_bucket histogram",
            ]
        )
        for (method, path, bucket), value in sorted(self.request_duration_buckets.items()):
            lines.append(
                f'http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="{bucket}"}} {value}'
            )

        lines.append("")
        return "\n".join(lines)


metrics = MetricStore()
app = FastAPI(title="Prometheus Metrics Middleware Demo")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next) -> Response:
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        cost_seconds = time.perf_counter() - start
        metrics.record_request(request.method, request.url.path, 500, cost_seconds)
        logger.exception("请求发生未处理异常")
        raise

    cost_seconds = time.perf_counter() - start
    metrics.record_request(
        request.method,
        request.url.path,
        response.status_code,
        cost_seconds,
    )
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    try:
        return {"reply": f"收到：{request.message}"}
    except Exception as exc:
        logger.exception("聊天接口发生未知错误")
        raise HTTPException(status_code=500, detail="聊天服务暂时不可用") from exc


@app.get("/boom")
def boom() -> dict[str, str]:
    raise HTTPException(status_code=500, detail="模拟服务错误")


@app.get("/metrics", response_class=PlainTextResponse)
def read_metrics() -> str:
    return metrics.render()


def run_local_demo() -> None:
    client = TestClient(app)

    print("\n=== 场景1：制造几次业务请求 ===")
    print("GET /health:", client.get("/health").status_code)
    print("POST /chat:", client.post("/chat", json={"message": "指标怎么暴露？"}).status_code)
    print("POST /chat 参数错误:", client.post("/chat", json={"message": "短"}).status_code)
    print("GET /boom:", client.get("/boom").status_code)

    print("\n=== 场景2：查看 /metrics ===")
    response = client.get("/metrics")
    print(response.text)


if __name__ == "__main__":
    run_local_demo()

