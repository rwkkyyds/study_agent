"""客服 Agent 工具：知识库搜索、订单查询和转人工。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.ticket import Message, Ticket
from app.rag.retriever import RetrievedChunk, Retriever


@dataclass(frozen=True)
class HumanTransferResult:
    """转人工工具的结果。"""

    ticket_id: int
    status: str
    message: str


class CustomerServiceTools:
    """封装客服工作流可调用的领域工具。"""

    def __init__(self, retriever: Retriever, db: Session) -> None:
        self.retriever = retriever
        self.db = db

    def search_knowledge(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """搜索知识库，不在工具层复制向量化逻辑。"""

        return self.retriever.search(query, top_k=top_k)

    def lookup_order(self, query: str) -> dict[str, Any]:
        """返回订单查询的本地替身结果，阶段五再接入真实订单服务。"""

        return {
            "order_id": self._extract_order_id(query),
            "status": "待查询",
            "message": "订单系统适配器将在后续阶段接入。",
        }

    def transfer_to_human(self, customer_id: int, query: str) -> HumanTransferResult:
        """创建人工客服工单，并记录首条系统消息。"""

        ticket = Ticket(
            title=query[:255],
            description=query,
            status="open",
            priority="normal",
            customer_id=customer_id,
        )
        self.db.add(ticket)
        self.db.flush()
        self.db.add(
            Message(
                ticket_id=ticket.id,
                sender_id=customer_id,
                sender_role="system",
                content="已为您创建人工客服工单。",
                msg_type="system",
            )
        )
        self.db.commit()
        self.db.refresh(ticket)
        return HumanTransferResult(
            ticket_id=ticket.id,
            status=ticket.status,
            message="已转接人工客服，请耐心等待。",
        )

    @staticmethod
    def _extract_order_id(query: str) -> str | None:
        tokens = query.replace("#", " ").split()
        for token in tokens:
            if token.isdigit():
                return token
        return None
