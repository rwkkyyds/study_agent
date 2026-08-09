"""客服对话 API。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.rag.retriever import Retriever
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.auth import get_current_user
from app.stability.factory import build_rate_limiter, build_redis_client, build_session_memory
from app.stability.memory import SessionMemory
from app.stability.metrics import Metrics
from app.tools.customer_service import CustomerServiceTools
from app.workflow.customer_service import CustomerServiceWorkflow

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()
redis_client = build_redis_client(settings.redis_url)
rate_limiter = build_rate_limiter(settings, redis_client)
session_memory = build_session_memory(settings, redis_client)
metrics = Metrics()


def get_retriever() -> Retriever:
    """提供默认检索服务；后续可替换为应用生命周期单例。"""

    return Retriever()


def get_rate_limiter():
    return rate_limiter


def get_session_memory() -> SessionMemory:
    return session_memory


def get_metrics() -> Metrics:
    return metrics


def get_workflow(
    db: Session = Depends(get_db),
    retriever: Retriever = Depends(get_retriever),
) -> CustomerServiceWorkflow:
    """组装工作流依赖，避免路由直接操作工具和状态图。"""

    return CustomerServiceWorkflow(CustomerServiceTools(retriever=retriever, db=db))


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    workflow: CustomerServiceWorkflow = Depends(get_workflow),
    limiter=Depends(get_rate_limiter),
    memory: SessionMemory = Depends(get_session_memory),
    request_metrics: Metrics = Depends(get_metrics),
) -> ChatResponse:
    """执行一次需要登录的客服对话，并记录短期会话上下文。"""

    if not limiter.allow(str(current_user.id)):
        request_metrics.record_request(429)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
            headers={"Retry-After": str(settings.rate_limit_window_seconds)},
        )

    memory.append(current_user.id, "user", request.query)
    state = workflow.run(customer_id=current_user.id, query=request.query)
    memory.append(current_user.id, "assistant", state["answer"])
    request_metrics.record_request(200, state["intent"])
    return ChatResponse(
        answer=state["answer"],
        intent=state["intent"],
        sources=state.get("sources", []),
        ticket_id=state.get("ticket_id"),
        order=state.get("order"),
    )
