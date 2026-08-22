"""AI 面试业务接口。"""

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.interview import (
    AnswerSubmissionRequest,
    FollowUpStreamTokenRequest,
    FollowUpStreamTokenResponse,
    InterviewFollowUpRequest,
    InterviewFollowUpResponse,
    InterviewQuestionRequest,
    InterviewReportResponse,
    InterviewSessionDetailResponse,
    InterviewSessionListResponse,
    InterviewSessionResponse,
)
from app.core.config import get_settings
from app.services.auth import create_follow_up_stream_token, decode_follow_up_stream_token, get_current_user
from app.services.interviews import InterviewPersistenceService

router = APIRouter(prefix="/interviews", tags=["interviews"])
interview_service = InterviewPersistenceService()
settings = get_settings()


@router.get("/sessions", response_model=InterviewSessionListResponse)
def list_interview_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewSessionListResponse:
    """返回当前用户的历史面试会话列表。"""

    return interview_service.list_owned_sessions(db=db, current_user=current_user)


@router.get("/sessions/{session_id}", response_model=InterviewSessionDetailResponse)
def get_interview_session_detail(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewSessionDetailResponse:
    """返回当前用户某次面试的聚合详情。"""

    detail = interview_service.get_owned_session_detail(db=db, current_user=current_user, session_id=session_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    return detail


@router.post("/questions", response_model=InterviewSessionResponse)
def generate_questions(
    request: InterviewQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewSessionResponse:
    """根据简历和岗位生成一轮结构化面试题，并保存到当前用户下。"""

    try:
        return interview_service.generate_questions(db=db, current_user=current_user, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/follow-up", response_model=InterviewFollowUpResponse)
def generate_follow_up(
    request: InterviewFollowUpRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewFollowUpResponse:
    """根据候选人单题回答生成多轮追问，并保存追问快照。"""

    try:
        response = interview_service.generate_follow_up(db=db, current_user=current_user, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    return response


@router.post("/follow-up/stream-token", response_model=FollowUpStreamTokenResponse)
def create_follow_up_stream_access_token(
    request: FollowUpStreamTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUpStreamTokenResponse:
    """用登录态 JWT 换取短期 SSE 访问 Token。"""

    session = interview_service.get_owned_session(db=db, current_user=current_user, session_id=request.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")

    token = create_follow_up_stream_token(
        user_id=current_user.id,
        session_id=request.session_id,
        question_id=request.question_id,
        answer=request.answer,
    )
    return FollowUpStreamTokenResponse(
        stream_token=token,
        expires_in=settings.stream_token_expire_minutes * 60,
    )


@router.get("/follow-up/stream")
def stream_follow_up(
    token: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """通过短期 Token 输出追问生成过程的 SSE 事件。"""

    payload = decode_follow_up_stream_token(token)
    session = interview_service.get_owned_session_by_user_id(
        db=db,
        user_id=payload["sub"],
        session_id=payload["session_id"],
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的流式 Token")

    request = InterviewFollowUpRequest(
        session_id=payload["session_id"],
        question_id=payload["question_id"],
        answer=payload["answer"],
    )

    def event_stream() -> Iterator[str]:
        try:
            current_user = User(id=payload["sub"], username="", hashed_password="", role="candidate", is_active=True)
            response = interview_service.generate_follow_up(db=db, current_user=current_user, request=request)
            if response is None:
                yield _sse_event("error", {"message": "面试会话不存在"})
                return
            for trace in response.workflow_trace:
                yield _sse_event("trace", {"node": trace})
            for follow_up in response.follow_up_questions:
                yield _sse_event("follow_up", {"question": follow_up})
            yield _sse_event("done", response.model_dump())
        except Exception as exc:  # pragma: no cover - 兜底保护，正常错误已在接口层处理
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/evaluate", response_model=InterviewReportResponse)
def evaluate_answers(
    request: AnswerSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewReportResponse:
    """提交候选人回答、生成评分报告，并保存报告快照。"""

    try:
        report = interview_service.evaluate_answers(db=db, current_user=current_user, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    return report


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
