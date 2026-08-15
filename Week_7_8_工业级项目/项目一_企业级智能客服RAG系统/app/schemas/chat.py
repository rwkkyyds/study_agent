"""客服对话请求与响应 Schema。"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """普通客服对话请求。"""

    query: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    model: str | None = Field(
        None,
        description="通义千问模型名称，可选值：qwen-turbo / qwen-plus / qwen-max / qwen-coder-plus / qwen-coder-turbo",
    )


class SourceItem(BaseModel):
    """知识库召回来源。"""

    id: str
    score: float
    metadata: dict = Field(default_factory=dict)
    content: str | None = None


class ChatResponse(BaseModel):
    """客服工作流统一响应。"""

    answer: str
    intent: str
    model: str | None = Field(None, description="实际使用的模型名称")
    sources: list[SourceItem] = Field(default_factory=list)
    ticket_id: int | None = None
    order: dict | None = None
