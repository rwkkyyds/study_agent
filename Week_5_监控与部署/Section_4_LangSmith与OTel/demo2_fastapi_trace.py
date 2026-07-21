"""FastAPI 请求级链路追踪 demo：只依赖项目已有的 FastAPI/Uvicorn。"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from typing import Iterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("fastapi-trace")
app = FastAPI(title="Local Trace Demo")


class AgentRequest(BaseModel):
    question: str = Field(min_length=2, max_length=200)
    top_k: int = Field(default=3, ge=1, le=10)


@contextmanager
def span(name: str, trace_id: str, parent_id: str | None = None) -> Iterator[str]:
    """用日志模拟 span 生命周期；真实 OTel 接入时替换这里即可。"""

    span_id = uuid.uuid4().hex[:16]
    started = time.perf_counter()
    logger.info("span.start name=%s trace_id=%s span_id=%s parent_id=%s", name, trace_id, span_id, parent_id)
    try:
        yield span_id
    except Exception:
        logger.exception("span.error name=%s trace_id=%s", name, trace_id)
        raise
    finally:
        elapsed = (time.perf_counter() - started) * 1000
        logger.info("span.end name=%s trace_id=%s span_id=%s duration_ms=%.2f", name, trace_id, span_id, elapsed)


@app.middleware("http")
async def trace_request(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", uuid.uuid4().hex)
    request.state.trace_id = trace_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request.error method=%s path=%s trace_id=%s", request.method, request.url.path, trace_id)
        raise
    response.headers["X-Trace-Id"] = trace_id
    logger.info("request.end method=%s path=%s status=%s trace_id=%s duration_ms=%.2f", request.method, request.url.path, response.status_code, trace_id, (time.perf_counter() - started) * 1000)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "trace_id": getattr(request.state, "trace_id", "unknown")})


@app.post("/agent/run")
async def run_agent(payload: AgentRequest, request: Request):
    trace_id = request.state.trace_id
    with span("agent.run", trace_id) as root_id:
        with span("retriever.search", trace_id, root_id):
            await __import__("asyncio").sleep(0.01)
        with span("llm.generate", trace_id, root_id):
            await __import__("asyncio").sleep(0.01)
    return {"trace_id": trace_id, "answer": f"已处理：{payload.question}", "top_k": payload.top_k}


@app.get("/health")
async def health():
    return {"status": "ok"}
