"""客服对话 API。"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.rag.embeddings import DashScopeEmbedding
from app.rag.llm import QwenLLM
from app.rag.retriever import Retriever, get_shared_retriever
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.auth import get_current_user
from app.stability.factory import build_rate_limiter, build_redis_client, build_session_memory
from app.stability.memory import SessionMemory
from app.stability.metrics import Metrics
from app.tools.customer_service import CustomerServiceTools
from app.workflow.customer_service import CustomerServiceWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()
redis_client = build_redis_client(settings.redis_url)
rate_limiter = build_rate_limiter(settings, redis_client)
session_memory = build_session_memory(settings, redis_client)
metrics = Metrics()


def get_retriever() -> Retriever:
    """
    提供默认检索服务。
    生产环境优先使用 DashScopeEmbedding，API Key 不存在时回退到本地 MockEmbedding。
    """

    return get_shared_retriever()


def get_llm() -> QwenLLM | None:
    """提供 LLM 回答生成服务。API Key 不存在时返回 None（跳过 LLM 回答）。"""

    if settings.dashscope_api_key:
        return QwenLLM(dashscope_api_key=settings.dashscope_api_key)
    return None


def get_rate_limiter():
    return rate_limiter


def get_session_memory() -> SessionMemory:
    return session_memory


def get_metrics() -> Metrics:
    return metrics


def get_workflow(
    db: Session = Depends(get_db),
    retriever: Retriever = Depends(get_retriever),
    llm: QwenLLM | None = Depends(get_llm),
) -> CustomerServiceWorkflow:
    """组装工作流依赖，避免路由直接操作工具和状态图。"""

    return CustomerServiceWorkflow(
        CustomerServiceTools(retriever=retriever, db=db),
        llm=llm,
    )


def _format_sse(event: str, payload: dict) -> str:
    """把 JSON payload 格式化为 SSE 事件。"""

    data = json.dumps(payload, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {data}\n\n"


def _iter_answer_chunks(answer: str, chunk_size: int = 12):
    """按小块输出文本，让前端呈现流式打字效果。"""

    for start in range(0, len(answer), chunk_size):
        yield answer[start:start + chunk_size]


def _validate_chat_request(
    request: ChatRequest,
    current_user: User,
    limiter,
    request_metrics: Metrics,
) -> str:
    """校验角色和限流，返回实际使用的模型名。"""

    if current_user.role != "customer":
        request_metrics.record_request(403)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="客服/管理员请使用客服工作台处理用户会话",
        )

    if not limiter.allow(str(current_user.id)):
        request_metrics.record_request(429)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
            headers={"Retry-After": str(settings.rate_limit_window_seconds)},
        )

    return request.model or "qwen-plus"


def _complete_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    workflow: CustomerServiceWorkflow = Depends(get_workflow),
    limiter=Depends(get_rate_limiter),
    memory: SessionMemory = Depends(get_session_memory),
    request_metrics: Metrics = Depends(get_metrics),
) -> ChatResponse:
    # 确定实际使用的模型：用户选择 → 默认 qwen-plus
    actual_model = _validate_chat_request(request, current_user, limiter, request_metrics)
    memory.append(current_user.id, "user", request.query)
    state = workflow.run(customer_id=current_user.id, query=request.query, model=request.model)
    memory.append(current_user.id, "assistant", state["answer"])
    request_metrics.record_request(200, state["intent"])
    return ChatResponse(
        answer=state["answer"],
        intent=state["intent"],
        model=actual_model,
        sources=state.get("sources", []),
        ticket_id=state.get("ticket_id"),
        order=state.get("order"),
    )


def _response_from_state(state: dict, actual_model: str, answer: str | None = None) -> ChatResponse:
    """将工作流 state 转成稳定的 ChatResponse。"""

    return ChatResponse(
        answer=state.get("answer", "") if answer is None else answer,
        intent=state["intent"],
        model=actual_model,
        sources=state.get("sources", []),
        ticket_id=state.get("ticket_id"),
        order=state.get("order"),
    )


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

    return _complete_chat(
        request=request,
        current_user=current_user,
        workflow=workflow,
        limiter=limiter,
        memory=memory,
        request_metrics=request_metrics,
    )


@router.post("/stream")
def stream_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    workflow: CustomerServiceWorkflow = Depends(get_workflow),
    limiter=Depends(get_rate_limiter),
    memory: SessionMemory = Depends(get_session_memory),
    request_metrics: Metrics = Depends(get_metrics),
) -> StreamingResponse:
    """SSE 流式客服对话，供前端聊天窗口逐步输出答案。"""

    actual_model = _validate_chat_request(request, current_user, limiter, request_metrics)

    def event_generator():
        yield _format_sse("chat.started", {"model": actual_model})
        try:
            memory.append(current_user.id, "user", request.query)
            final_response: ChatResponse | None = None
            for event in workflow.stream(
                customer_id=current_user.id,
                query=request.query,
                model=request.model,
            ):
                event_type = event["type"]
                if event_type == "metadata":
                    response = _response_from_state(event["state"], actual_model, answer="")
                    yield _format_sse("chat.metadata", response.model_dump(exclude={"answer"}))
                elif event_type == "delta":
                    yield _format_sse("chat.delta", {"delta": event["delta"]})
                elif event_type == "done":
                    final_response = _response_from_state(event["state"], actual_model)
                    memory.append(current_user.id, "assistant", final_response.answer)
                    request_metrics.record_request(200, final_response.intent)
                    yield _format_sse("chat.done", final_response.model_dump())

            if final_response is None:
                raise RuntimeError("chat stream ended without final response")
        except Exception as exc:
            logger.exception("chat_stream_failed user_id=%s", current_user.id)
            request_metrics.record_request(500)
            yield _format_sse(
                "chat.error",
                {"detail": "抱歉，我暂时无法处理您的请求，请稍后重试。", "error": str(exc)},
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
