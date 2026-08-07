"""客服 LangGraph 工作流。

流程：意图分类 → 条件路由 → 工具执行 → 统一响应。
本阶段使用确定性分类器，保留后续接入 LLM 分类器的边界。
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.models.user import User
from app.tools.customer_service import CustomerServiceTools

Intent = Literal["knowledge", "order", "human"]


class CustomerServiceState(TypedDict, total=False):
    """工作流状态，节点只读写自己负责的字段。"""

    customer_id: int
    query: str
    intent: Intent
    answer: str
    sources: list[dict]
    ticket_id: int | None
    order: dict
    error: str | None


class IntentClassifier:
    """基于关键词的可测试分类器，后续可替换为模型 Provider。"""

    HUMAN_KEYWORDS = ("人工", "客服", "投诉", "举报", "转接")
    ORDER_KEYWORDS = ("订单", "物流", "快递", "配送", "发货", "退款进度")

    def classify(self, query: str) -> Intent:
        normalized = query.lower()
        if any(keyword in normalized for keyword in self.HUMAN_KEYWORDS):
            return "human"
        if any(keyword in normalized for keyword in self.ORDER_KEYWORDS):
            return "order"
        return "knowledge"


class CustomerServiceWorkflow:
    """客服工作流门面，负责构建和执行编译后的 StateGraph。"""

    def __init__(self, tools: CustomerServiceTools, classifier: IntentClassifier | None = None) -> None:
        self.tools = tools
        self.classifier = classifier or IntentClassifier()
        self.graph = self._build_graph()

    def run(self, customer_id: int, query: str) -> CustomerServiceState:
        """执行一次客服请求，并返回最终状态。"""

        if not query.strip():
            raise ValueError("query 不能为空")
        return self.graph.invoke({
            "customer_id": customer_id,
            "query": query,
            "ticket_id": None,
            "sources": [],
        })

    def _build_graph(self):
        graph = StateGraph(CustomerServiceState)
        graph.add_node("classify_intent", self._classify_intent)
        graph.add_node("knowledge_search", self._knowledge_search)
        graph.add_node("order_lookup", self._order_lookup)
        graph.add_node("transfer_to_human", self._transfer_to_human)
        graph.add_edge(START, "classify_intent")
        graph.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "knowledge": "knowledge_search",
                "order": "order_lookup",
                "human": "transfer_to_human",
            },
        )
        graph.add_edge("knowledge_search", END)
        graph.add_edge("order_lookup", END)
        graph.add_edge("transfer_to_human", END)
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
                "answer": "暂未在知识库找到相关内容，您可以输入“转人工”联系人工客服。",
                "sources": [],
            }
        return {
            "answer": results[0].content,
            "sources": [
                {"id": item.id, "score": item.score, "metadata": item.metadata}
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
