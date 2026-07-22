"""
demo2：OpenTelemetry 手动 Span 基础

这个文件演示：
1. trace 是一次完整请求
2. span 是请求中的一个子步骤
3. attribute/event 用来记录关键上下文
4. 缺少 OpenTelemetry 包时降级为本地可读输出

运行方式：
    python demo2_otel_manual_span.py
"""

from __future__ import annotations

from contextlib import contextmanager
import logging
import time
from typing import Iterator


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


def setup_tracer():
    if not OTEL_AVAILABLE:
        logger.warning("未安装 OpenTelemetry SDK，使用本地降级 Span 输出")
        return None

    resource = Resource.create(
        {"service.name": "ai-agent-bootcamp-demo"}
    )  # 【service.name】标记这批 trace 属于哪个服务
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        SimpleSpanProcessor(ConsoleSpanExporter())
    )  # 【ConsoleSpanExporter】把 span 打印到控制台，适合教学和本地调试
    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)


@contextmanager
def local_span(name: str) -> Iterator[None]:
    start = time.perf_counter()
    logger.info("[local-span-start] %s", name)
    try:
        yield
        cost_ms = (time.perf_counter() - start) * 1000
        logger.info("[local-span-end] %s cost_ms=%.2f", name, cost_ms)
    except Exception:
        logger.exception("[local-span-error] %s", name)
        raise


def retrieve_documents(query: str) -> list[str]:
    time.sleep(0.05)
    return [
        "trace 是一次完整请求的追踪记录。",
        "span 是 trace 里的一个子步骤，比如检索、重排、模型调用。",
    ]


def generate_answer(query: str, docs: list[str]) -> str:
    time.sleep(0.08)
    return f"问题：{query}。答案：本次命中 {len(docs)} 条上下文，trace 用来串起完整链路。"


def run_with_real_otel(query: str) -> str:
    tracer = setup_tracer()
    assert tracer is not None

    with tracer.start_as_current_span("rag_request") as root_span:
        # 【attribute】记录可检索、可聚合的键值信息，不要放密码等敏感数据。
        root_span.set_attribute("app.query_length", len(query))
        root_span.add_event("request.received")

        with tracer.start_as_current_span("retrieve_documents") as retrieve_span:
            docs = retrieve_documents(query)
            retrieve_span.set_attribute("retrieval.doc_count", len(docs))

        with tracer.start_as_current_span("generate_answer") as llm_span:
            answer = generate_answer(query, docs)
            llm_span.set_attribute("llm.output_length", len(answer))

        root_span.add_event("request.finished")
        return answer


def run_with_local_fallback(query: str) -> str:
    with local_span("rag_request"):
        logger.info("attribute app.query_length=%s", len(query))
        logger.info("event request.received")

        with local_span("retrieve_documents"):
            docs = retrieve_documents(query)
            logger.info("attribute retrieval.doc_count=%s", len(docs))

        with local_span("generate_answer"):
            answer = generate_answer(query, docs)
            logger.info("attribute llm.output_length=%s", len(answer))

        logger.info("event request.finished")
        return answer


def run_local_demo() -> None:
    query = "trace 和 span 有什么区别？"
    answer = run_with_real_otel(query) if OTEL_AVAILABLE else run_with_local_fallback(query)

    print("\n=== OpenTelemetry Manual Span Demo ===")
    print(answer)
    print("观察重点：一个 rag_request trace 下包含 retrieve_documents 和 generate_answer 两个子步骤")


if __name__ == "__main__":
    run_local_demo()

