"""客服对话 API。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.rag.retriever import Retriever
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.auth import get_current_user
from app.tools.customer_service import CustomerServiceTools
from app.workflow.customer_service import CustomerServiceWorkflow

router = APIRouter(prefix="/chat", tags=["chat"])


def get_retriever() -> Retriever:
    """提供默认检索服务；阶段五可替换为应用生命周期单例。"""

    return Retriever()


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
) -> ChatResponse:
    """执行一次需要登录的客服对话。"""

    state = workflow.run(customer_id=current_user.id, query=request.query)
    return ChatResponse(
        answer=state["answer"],
        intent=state["intent"],
        sources=state.get("sources", []),
        ticket_id=state.get("ticket_id"),
        order=state.get("order"),
    )
