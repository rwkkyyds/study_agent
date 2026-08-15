"""工单相关的 Pydantic Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class TicketReplyRequest(BaseModel):
    """客服回复工单的请求体。"""

    content: str = Field(..., min_length=1, max_length=2000, description="回复内容")


class TicketMessageResponse(BaseModel):
    """工单消息响应体。"""

    id: int
    ticket_id: int
    sender_id: int
    sender_role: str
    content: str
    msg_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    """工单列表项/详情响应体。"""

    id: int
    title: str
    description: str
    status: str
    priority: str
    customer_id: int
    agent_id: int | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[TicketMessageResponse] | None = None

    model_config = {"from_attributes": True}