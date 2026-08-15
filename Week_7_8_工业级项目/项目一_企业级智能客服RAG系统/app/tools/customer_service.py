"""客服 Agent 工具：知识库搜索、订单查询和转人工。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.ticket import Message, Ticket
from app.rag.retriever import RetrievedChunk, Retriever
from app.services.ticket_events import publish_ticket_created


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
        """返回订单查询结果，包含模拟订单数据。"""

        order_id = self._extract_order_id(query) or "ORD-20240701-0001"
        mock_orders = {
            "ORD-20240701-0001": {
                "order_id": "ORD-20240701-0001",
                "status": "已发货",
                "product": "智能客服 RAG 系统 - 企业版",
                "amount": "¥29,800.00",
                "logistics": "顺丰快递 SF1234567890",
                "estimated_delivery": "2024-07-05",
                "message": "您的订单已通过顺丰快递发出，预计 7月5日 送达。",
            },
            "ORD-20240701-0002": {
                "order_id": "ORD-20240701-0002",
                "status": "待发货",
                "product": "知识库文档解析服务包",
                "amount": "¥5,800.00",
                "logistics": "待出库",
                "estimated_delivery": "2024-07-08",
                "message": "您的订单正在仓库准备中，预计 7月6日 前发出。",
            },
            "ORD-20240701-0003": {
                "order_id": "ORD-20240701-0003",
                "status": "已完成",
                "product": "AI 客服年度订阅 - 基础版",
                "amount": "¥15,000.00",
                "logistics": "已签收",
                "estimated_delivery": "2024-06-28",
                "message": "订单已完成，感谢您的购买。如需续费请联系客服。",
            },
        }
        result = mock_orders.get(order_id)
        if result:
            return result
        return {
            "order_id": order_id,
            "status": "未找到",
            "message": f"未找到订单 {order_id}，请核对订单号后重试。",
        }

    def transfer_to_human(self, customer_id: int, query: str) -> HumanTransferResult:
        """创建人工客服工单，并把用户诉求写入同一个工单消息流。"""

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
                sender_role="customer",
                content=query.strip(),
                msg_type="text",
            )
        )
        self.db.add(
            Message(
                ticket_id=ticket.id,
                sender_id=customer_id,
                sender_role="system",
                content="正在为您转接人工客服，请稍候。",
                msg_type="system",
            )
        )
        self.db.commit()
        self.db.refresh(ticket)
        publish_ticket_created(ticket)
        return HumanTransferResult(
            ticket_id=ticket.id,
            status=ticket.status,
            message="正在为您转接人工客服，请稍候。",
        )

    @staticmethod
    def _extract_order_id(query: str) -> str | None:
        tokens = query.replace("#", " ").split()
        for token in tokens:
            if token.isdigit():
                return token
        return None
