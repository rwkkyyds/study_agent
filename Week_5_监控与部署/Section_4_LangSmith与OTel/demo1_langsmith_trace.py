"""
demo1：LangSmith 链路追踪基础

这个文件演示：
1. 用 @traceable 标记一次 AI 应用调用
2. 把检索、Prompt 构造、模型调用拆成父子步骤
3. 没有 LANGSMITH_API_KEY 时仍然能本地运行

运行方式：
    python demo1_langsmith_trace.py
"""

from __future__ import annotations

import logging
import os
from typing import List

from langsmith import traceable, tracing_context
from pydantic import BaseModel, Field


logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=200)


class AnswerResponse(BaseModel):
    question: str
    context_count: int
    answer: str


KNOWLEDGE_BASE = [
    "LangSmith 适合观察 LLM、Agent、RAG 的输入输出和中间步骤。",
    "OpenTelemetry 是通用可观测性标准，可以追踪服务、数据库和消息队列。",
    "trace 表示一次完整请求，span 表示这次请求中的一个子步骤。",
]


@traceable(name="retrieve_context", run_type="retriever") 
def retrieve_context(question: str) -> List[str]:
    # 【retriever】这里模拟 RAG 检索：真实项目会查向量库或数据库。
    keywords = question.lower().split()
    matched_docs = [
        doc for doc in KNOWLEDGE_BASE if any(word in doc.lower() for word in keywords)
    ]
    return matched_docs or KNOWLEDGE_BASE[:1]


@traceable(name="build_prompt", run_type="chain")
def build_prompt(question: str, contexts: List[str]) -> str:
    # 【prompt】把用户问题和检索上下文拼成模型输入，方便 LangSmith 展示中间输入。
    context_text = "\n".join(f"- {item}" for item in contexts)
    return f"请基于资料回答问题。\n资料：\n{context_text}\n问题：{question}"


@traceable(name="fake_llm_call", run_type="llm")
def fake_llm_call(prompt: str) -> str:
    # 【llm】这里不用真实大模型，避免没有 API Key 时跑不起来。
    if "LangSmith" in prompt:
        return "LangSmith 用来追踪 LLM/Agent/RAG 调用，能看到输入、输出和中间步骤。"
    return "可观测性用于记录请求链路、耗时、错误和关键业务上下文。"


@traceable(name="answer_question", run_type="chain")
def answer_question(request: QuestionRequest) -> AnswerResponse:
    contexts = retrieve_context(request.question)
    prompt = build_prompt(request.question, contexts)
    answer = fake_llm_call(prompt)
    return AnswerResponse(
        question=request.question,
        context_count=len(contexts),
        answer=answer,
    )


def is_langsmith_enabled() -> bool:
    # 【LANGSMITH_API_KEY】没有 Key 时关闭在线上报，但 @traceable 包装函数仍能正常执行。
    return bool(os.getenv("LANGSMITH_API_KEY"))


def run_local_demo() -> None:
    request = QuestionRequest(question="LangSmith 能观察什么？")
    enabled = is_langsmith_enabled()

    logger.info("LangSmith 在线追踪启用状态：%s", enabled)
    if not enabled:
        logger.info("未检测到 LANGSMITH_API_KEY，本次只演示本地调用链路")

    # 【tracing_context】统一控制本次调用是否上报到 LangSmith 平台。
    with tracing_context(enabled=enabled):
        response = answer_question(request)

    print("\n=== LangSmith Trace Demo ===")
    print("问题:", response.question)
    print("命中文档数:", response.context_count)
    print("回答:", response.answer)
    print("\n观察重点：answer_question -> retrieve_context/build_prompt/fake_llm_call")


if __name__ == "__main__":
    run_local_demo()

