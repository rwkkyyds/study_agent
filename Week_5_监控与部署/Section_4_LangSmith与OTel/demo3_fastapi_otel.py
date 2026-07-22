"""
demo3：FastAPI 请求链路追踪

这个文件演示：
1. 用 FastAPI middleware 包住每次请求
2. 为 HTTP 请求创建 span 或本地 trace 日志
3. 记录 method、path、status_code、cost_ms
4. 用 TestClient 本地验证，不必须启动 uvicorn

运行方式：
    python demo3_fastapi_otel.py
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    trace = None
    Resource = None
    TracerProvider = None
    ConsoleSpanExporter = None
    SimpleSpanProcessor = None
    OTEL_AVAILABLE = False


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=200)


class ChatResponse(BaseModel):
    reply: str
    trace_mode: str


def setup_tracer():
    if not OTEL_AVAILABLE:
        logger.warning("未安装 OpenTelemetry SDK，FastAPI middleware 使用本地 trace 日志")
        return None

    resource = Resource.create({"service.name": "fastapi-otel-demo"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)


tracer = setup_tracer()
app = FastAPI(title="FastAPI OpenTelemetry Demo")


@app.middleware("http")
async def trace_http_request(request: Request, call_next) -> Response:
    # 【middleware】每个请求进入接口函数前会先经过这里，适合统一记录耗时和状态码。
    span_name = f"HTTP {request.method} {request.url.path}"
    start = time.perf_counter()

    if tracer:
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.route", request.url.path)
            try:
                response = await call_next(request)
                span.set_attribute("http.status_code", response.status_code)
                return response
            except Exception as exc:
                span.record_exception(exc)  # 【record_exception】把异常写进 span，方便排查错误请求。
                span.set_attribute("error", True)
                raise

    trace_id = uuid.uuid4().hex[:12]
    logger.info("[trace-start] id=%s name=%s", trace_id, span_name)
    try:
        response = await call_next(request)
        cost_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "[trace-end] id=%s status=%s cost_ms=%.2f",
            trace_id,
            response.status_code,
            cost_ms,
        )
        return response
    except Exception:
        cost_ms = (time.perf_counter() - start) * 1000
        logger.exception("[trace-error] id=%s cost_ms=%.2f", trace_id, cost_ms)
        raise


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        reply = f"收到：{request.message}。这次请求已经被 middleware 记录。"
        return ChatResponse(
            reply=reply,
            trace_mode="opentelemetry" if OTEL_AVAILABLE else "local-fallback",
        )
    except Exception as exc:
        logger.exception("聊天接口发生未知错误")
        raise HTTPException(status_code=500, detail="聊天服务暂时不可用") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def run_local_demo() -> None:
    client = TestClient(app)

    print("\n=== 场景1：健康检查请求 ===")
    response = client.get("/health")
    print("状态码:", response.status_code)
    print("响应:", response.json())

    print("\n=== 场景2：聊天请求 ===")
    response = client.post("/chat", json={"message": "如何观察 FastAPI 请求？"})
    print("状态码:", response.status_code)
    print("响应:", response.json())

    print("\n=== 场景3：参数校验失败请求 ===")
    response = client.post("/chat", json={"message": "短"})
    print("状态码:", response.status_code)
    print("响应:", response.json())


if __name__ == "__main__":
    run_local_demo()

