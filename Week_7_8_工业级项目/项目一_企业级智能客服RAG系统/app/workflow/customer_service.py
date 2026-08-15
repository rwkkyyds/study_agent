"""客服 LangGraph 工作流。

流程：意图分类 → 条件路由 → 工具执行 → LLM 生成回答。
本阶段使用确定性分类器，保留后续接入 LLM 分类器的边界。
"""

from __future__ import annotations

import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.models.user import User
from app.rag.llm import QwenLLM
from app.tools.customer_service import CustomerServiceTools

logger = logging.getLogger(__name__)

Intent = Literal["knowledge", "order", "human", "unknown"]


class CustomerServiceState(TypedDict, total=False):
    """工作流状态，节点只读写自己负责的字段。"""

    customer_id: int
    query: str
    model: str | None  # 用户选择的模型名称，None 表示使用 LLM 默认值
    intent: Intent
    answer: str
    sources: list[dict]
    ticket_id: int | None
    order: dict
    error: str | None


class IntentClassifier:
    """支持 LLM 分类的意图分类器，LLM 不可用时回退关键词匹配。"""

    HUMAN_KEYWORDS = ("人工", "客服", "投诉", "举报", "转接")
    ORDER_KEYWORDS = ("订单", "物流", "快递", "配送", "发货", "退款进度")

    CLASSIFY_PROMPT = """你是一个智能客服系统的意图分类器。请判断用户问题的意图，只返回以下一个词：
- knowledge：用户询问知识库内容（如产品介绍、规则说明、常见问题、文档查询）
- order：用户查询订单、物流、退款进度
- human：用户要求转接人工客服或投诉
- unknown：其他问题，如问候、闲聊、天气、一般性对话，或无法明确分类的请求

用户问题：{query}

分类结果（只输出一个词）："""

    def __init__(self, llm: QwenLLM | None = None) -> None:
        self.llm = llm

    def classify(self, query: str) -> Intent:
        # 明确的业务入口优先走确定性规则，避免 LLM 把“转人工”等短句误判为闲聊。
        normalized = query.lower()
        if any(keyword in normalized for keyword in self.HUMAN_KEYWORDS):
            return "human"
        if any(keyword in normalized for keyword in self.ORDER_KEYWORDS):
            return "order"

        # 优先使用 LLM 分类
        if self.llm is not None:
            try:
                result = self.llm.generate(
                    query=self.CLASSIFY_PROMPT.format(query=query),
                    context="",
                ).strip().lower()
                if result in ("knowledge", "order", "human", "unknown"):
                    return result  # type: ignore[return-value]
                logger.debug("LLM 分类结果 '%s' 不在预期中，回退关键词", result)
            except Exception as exc:
                logger.warning("LLM 分类失败，回退关键词: %s", exc)

        return "knowledge"


class CustomerServiceWorkflow:
    """客服工作流门面，负责构建和执行编译后的 StateGraph。"""

    def __init__(
        self,
        tools: CustomerServiceTools,
        classifier: IntentClassifier | None = None,
        llm: QwenLLM | None = None,
    ) -> None:
        self.tools = tools
        self.llm = llm
        self.classifier = classifier or IntentClassifier(llm=llm)
        self.graph = self._build_graph()

    def run(self, customer_id: int, query: str, model: str | None = None) -> CustomerServiceState:
        """执行一次客服请求，并返回最终状态。

        Args:
            customer_id: 用户 ID。
            query: 用户问题。
            model: 用户选择的模型名称，None 表示使用 LLM 默认值。
        """

        if not query.strip():
            raise ValueError("query 不能为空")
        return self.graph.invoke({
            "customer_id": customer_id,
            "query": query,
            "model": model,
            "ticket_id": None,
            "sources": [],
        })

    def stream(self, customer_id: int, query: str, model: str | None = None):
        """执行客服请求并在最终回答生成阶段逐块返回。

        事件字典：
        - {"type": "metadata", "state": {...}}：意图、来源、工单等元数据
        - {"type": "delta", "delta": "..."}：回答增量文本
        - {"type": "done", "state": {...}}：包含完整 answer 的最终状态
        """

        if not query.strip():
            raise ValueError("query 不能为空")

        intent = self.classifier.classify(query)

        if intent == "knowledge":
            yield from self._stream_knowledge(customer_id, query, model, intent)
            return
        if intent == "order":
            state: CustomerServiceState = {
                "customer_id": customer_id,
                "query": query,
                "model": model,
                "intent": intent,
                **self._order_lookup({"query": query}),
            }
            yield from self._stream_static_state(state)
            return
        if intent == "human":
            state = {
                "customer_id": customer_id,
                "query": query,
                "model": model,
                "intent": intent,
                **self._transfer_to_human({"customer_id": customer_id, "query": query}),
            }
            yield from self._stream_static_state(state)
            return

        yield from self._stream_unknown(customer_id, query, model, intent)

    @staticmethod
    def _source_payload(results) -> list[dict]:
        return [
            {
                "id": item.id,
                "score": item.score,
                "metadata": item.metadata,
                "content": item.content[:240],
            }
            for item in results
        ]

    @staticmethod
    def _text_chunks(text: str, chunk_size: int = 12):
        for start in range(0, len(text), chunk_size):
            yield text[start:start + chunk_size]

    def _stream_static_state(self, state: CustomerServiceState):
        metadata = {key: value for key, value in state.items() if key != "answer"}
        yield {"type": "metadata", "state": metadata}
        answer = state.get("answer", "")
        for chunk in self._text_chunks(answer):
            yield {"type": "delta", "delta": chunk}
        yield {"type": "done", "state": state}

    def _stream_knowledge(
        self,
        customer_id: int,
        query: str,
        model: str | None,
        intent: Intent,
    ):
        results = self.tools.search_knowledge(query)
        sources = self._source_payload(results)
        state: CustomerServiceState = {
            "customer_id": customer_id,
            "query": query,
            "model": model,
            "intent": intent,
            "sources": sources,
            "ticket_id": None,
        }

        if not results:
            state["answer"] = "暂未在知识库找到相关内容，您可以输入「转人工」联系人工客服。"
            yield from self._stream_static_state(state)
            return

        if self.llm is None:
            state["answer"] = results[0].content
            yield from self._stream_static_state(state)
            return

        yield {"type": "metadata", "state": {key: value for key, value in state.items() if key != "answer"}}
        context = self.tools.retriever.format_context(results)
        answer_parts: list[str] = []
        try:
            for chunk in self.llm.stream_generate(query=query, context=context, model=model):
                answer_parts.append(chunk)
                yield {"type": "delta", "delta": chunk}
            state["answer"] = "".join(answer_parts)
        except Exception as exc:
            logger.warning("LLM 流式生成回答失败，降级为直接返回检索结果: %s", exc)
            state["answer"] = results[0].content
            for chunk in self._text_chunks(state["answer"]):
                yield {"type": "delta", "delta": chunk}
        yield {"type": "done", "state": state}

    def _stream_unknown(
        self,
        customer_id: int,
        query: str,
        model: str | None,
        intent: Intent,
    ):
        state: CustomerServiceState = {
            "customer_id": customer_id,
            "query": query,
            "model": model,
            "intent": intent,
            "sources": [],
            "ticket_id": None,
        }

        if self.llm is None:
            state["answer"] = "抱歉，我暂时无法回答这个问题。您可以描述更具体的内容，或输入「转人工」联系人工客服。"
            yield from self._stream_static_state(state)
            return

        yield {"type": "metadata", "state": {key: value for key, value in state.items() if key != "answer"}}
        answer_parts: list[str] = []
        try:
            for chunk in self.llm.stream_generate(query=query, context="", model=model):
                answer_parts.append(chunk)
                yield {"type": "delta", "delta": chunk}
            state["answer"] = "".join(answer_parts)
        except Exception as exc:
            logger.warning("LLM 流式生成回答失败，降级为默认提示: %s", exc)
            state["answer"] = "抱歉，我暂时无法回答这个问题。您可以描述更具体的内容，或输入「转人工」联系人工客服。"
            for chunk in self._text_chunks(state["answer"]):
                yield {"type": "delta", "delta": chunk}
        yield {"type": "done", "state": state}

    def _build_graph(self):
        graph = StateGraph(CustomerServiceState)
        graph.add_node("classify_intent", self._classify_intent)
        graph.add_node("knowledge_search", self._knowledge_search)
        graph.add_node("order_lookup", self._order_lookup)
        graph.add_node("transfer_to_human", self._transfer_to_human)
        graph.add_node("unknown_intent", self._unknown_intent)
        graph.add_edge(START, "classify_intent")
        graph.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "knowledge": "knowledge_search",
                "order": "order_lookup",
                "human": "transfer_to_human",
                "unknown": "unknown_intent",
            },
        )
        graph.add_edge("knowledge_search", END)
        graph.add_edge("order_lookup", END)
        graph.add_edge("transfer_to_human", END)
        graph.add_edge("unknown_intent", END)
        return graph.compile()

    def _classify_intent(self, state: CustomerServiceState) -> dict:
        return {"intent": self.classifier.classify(state["query"])}

    @staticmethod
    def _route_by_intent(state: CustomerServiceState) -> Intent:
        return state["intent"]

    def _knowledge_search(self, state: CustomerServiceState) -> dict:
        results = self.tools.search_knowledge(state["query"])
        if not results:
            return {
                "answer": "暂未在知识库找到相关内容，您可以输入「转人工」联系人工客服。",
                "sources": [],
            }

        # 使用 LLM 生成回答（如果可用）
        if self.llm is not None:
            context = self.tools.retriever.format_context(results)
            try:
                answer = self.llm.generate(
                    query=state["query"],
                    context=context,
                    model=state.get("model"),
                )
            except Exception as exc:
                logger.warning("LLM 生成回答失败，降级为直接返回检索结果: %s", exc)
                answer = results[0].content
        else:
            answer = results[0].content

        return {
            "answer": answer,
            "sources": [
                {
                    "id": item.id,
                    "score": item.score,
                    "metadata": item.metadata,
                    "content": item.content[:240],
                }
                for item in results
            ],
        }

    def _order_lookup(self, state: CustomerServiceState) -> dict:
        result = self.tools.lookup_order(state["query"])
        return {"answer": result["message"], "sources": [], "order": result}

    def _transfer_to_human(self, state: CustomerServiceState) -> dict:
        result = self.tools.transfer_to_human(state["customer_id"], state["query"])
        return {
            "answer": result.message,
            "sources": [],
            "ticket_id": result.ticket_id,
        }

    def _unknown_intent(self, state: CustomerServiceState) -> dict:
        """处理未知意图（问候、闲聊、不相关的问题等），让 LLM 直接自然回答。"""
        if self.llm is not None:
            try:
                answer = self.llm.generate(
                    query=state["query"],
                    context="",
                    model=state.get("model"),
                )
                return {"answer": answer, "sources": []}
            except Exception as exc:
                logger.warning("LLM 生成回答失败，降级为默认提示: %s", exc)
        return {
            "answer": "抱歉，我暂时无法回答这个问题。您可以描述更具体的内容，或输入「转人工」联系人工客服。",
            "sources": [],
        }
