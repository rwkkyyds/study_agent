"""客服对话相关 Pydantic 请求/响应模型。"""

from __future__ import annotations

import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """用户发送消息请求。"""

    message: str = Field(..., min_length=1, max_length=2000, description="用户消息内容")
    ticket_id: Optional[int] = Field(None, description="续对话时传入已有工单 id")


class ChatResponse(BaseModel):
    """客服回复响应。"""

    reply: str = Field(..., description="Agent 回复内容")
    ticket_id: int = Field(..., description="工单 id")
    category: str = Field(..., description="分类")
    is_escalated: bool = Field(False, description="是否已转人工")
    sources: list[dict[str, Any]] = Field(default_factory=list, description="引用的知识库文档")


class TicketResponse(BaseModel):
    """工单信息响应。"""

    id: int
    customer_id: int
    assigned_to: Optional[int] = None
    title: str
    category: str
    priority: str
    status: str
    is_escalated: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """消息响应。"""

    id: int
    ticket_id: int
    sender: str
    content: str
    msg_type: str
    metadata: Optional[str] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}