"""FastAPI 监控 demo：零新增依赖暴露请求数、错误数和耗时。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("fastapi-metrics")
app = FastAPI(title="Prometheus Metrics Demo")


@dataclass
class Metrics:
    requests_total: int = 0
    errors_total: int = 0
    durations: list[float] = field(default_factory=list)

    def observe(self, duration_seconds: float, error: bool) -> None:
        self.requests_total += 1
        self.durations.append(duration_seconds)
        if error:
            self.errors_total += 1

    def render(self) -> str:
        total_duration = sum(self.durations)
        count = len(self.durations)
        return "\n".join(
            [
                "# HELP agent_requests_total Total agent requests.",
                "# TYPE agent_requests_total counter",
                f"agent_requests_total {self.requests_total}",
                "# HELP agent_errors_total Total agent errors.",
                "# TYPE agent_errors_total counter",
                f"agent_errors_total {self.errors_total}",
                "# HELP agent_request_duration_seconds_sum Sum of request durations.",
                "# TYPE agent_request_duration_seconds summary",
                f"agent_request_duration_seconds_sum {total_duration:.6f}",
                f"agent_request_duration_seconds_count {count}",
                "",
            ]
        )


metrics = Metrics()


class AgentRequest(BaseModel):
    question: str = Field(min_length=2, max_length=200)
    fail: bool = False


@app.middleware("http")
async def collect_metrics(request: Request, call_next):
    started = time.perf_counter()
    failed = False
    try:
        response = await call_next(request)
        failed = response.status_code >= 500
        return response
    except Exception:
        failed = True
        logger.exception("request.error path=%s", request.url.path)
        raise
    finally:
        elapsed = time.perf_counter() - started
        if request.url.path != "/metrics":
            metrics.observe(elapsed, failed)
        logger.info("request path=%s failed=%s duration_ms=%.2f", request.url.path, failed, elapsed * 1000)


@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> str:
    return metrics.render()


@app.post("/agent/run")
async def run_agent(payload: AgentRequest) -> dict[str, str]:
    try:
        await asyncio.sleep(0.01)
        if payload.fail:
            raise HTTPException(status_code=503, detail="模拟模型服务不可用")
        return {"answer": f"已处理：{payload.question}"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("agent.unexpected_error")
        raise HTTPException(status_code=500, detail="内部错误")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

