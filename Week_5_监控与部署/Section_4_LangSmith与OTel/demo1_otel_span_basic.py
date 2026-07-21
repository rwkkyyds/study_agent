"""本地演示 trace/span 的父子关系，不需要安装任何第三方依赖。"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class Span:
    """一次可观测操作：记录名称、父 span、属性、状态和耗时。"""

    name: str
    trace_id: str
    parent_id: str | None = None
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    attributes: dict[str, str | int | float] = field(default_factory=dict)
    status: str = "UNSET"
    duration_ms: float = 0.0

    def finish(self, started_at: float, status: str = "OK") -> None:
        self.duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        self.status = status

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@contextmanager
def start_span(name: str, trace_id: str, parent_id: str | None = None) -> Iterator[Span]:
    """创建并结束一个 span；异常会自动标记为 ERROR 后继续抛出。"""

    span = Span(name=name, trace_id=trace_id, parent_id=parent_id)
    started_at = time.perf_counter()
    try:
        yield span
    except Exception:
        span.finish(started_at, status="ERROR")
        logger.exception("span failed: %s", name)
        raise
    else:
        span.finish(started_at)
    logger.info("span=%s parent=%s status=%s %.2fms", span.name, span.parent_id, span.status, span.duration_ms)


def run_agent(question: str) -> dict[str, object]:
    """模拟一个 Agent 请求，展示根 span 下挂检索和生成两个子 span。"""

    trace_id = uuid.uuid4().hex
    spans: list[Span] = []
    with start_span("agent.run", trace_id) as root:
        root.attributes["question.length"] = len(question)
        spans.append(root)
        with start_span("retriever.search", trace_id, root.span_id) as retrieval:
            retrieval.attributes["documents.count"] = 3
            time.sleep(0.01)
            spans.append(retrieval)
        with start_span("llm.generate", trace_id, root.span_id) as generation:
            generation.attributes["model"] = "local-demo"
            time.sleep(0.015)
            spans.append(generation)
    return {"trace_id": trace_id, "answer": f"已处理问题：{question}", "spans": [s.as_dict() for s in spans]}


if __name__ == "__main__":
    print(json.dumps(run_agent("什么是父子 span？"), ensure_ascii=False, indent=2))
