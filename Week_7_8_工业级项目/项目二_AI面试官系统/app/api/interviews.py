"""AI 面试业务接口。"""

import json
from collections.abc import Iterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.interview import (
    AnswerSubmissionRequest,
    FollowUpStreamTokenRequest,
    FollowUpStreamTokenResponse,
    InterviewDraftListResponse,
    InterviewDraftRequest,
    InterviewDraftResponse,
    InterviewFollowUpRequest,
    InterviewFollowUpResponse,
    InterviewQuestionRequest,
    InterviewReportResponse,
    InterviewSessionDetailResponse,
    InterviewSessionListResponse,
    InterviewSessionResponse,
    InterviewTaskStatusResponse,
)
from app.schemas.auth import MessageResponse
from app.core.config import get_settings
from app.services.auth import create_follow_up_stream_token, decode_follow_up_stream_token, get_current_user
from app.services.interview_drafts import (
    clear_interview_drafts,
    delete_interview_draft,
    get_interview_drafts,
    save_interview_draft,
)
from app.services.interview_tasks import (
    create_interview_task,
    get_interview_task,
    mark_interview_task_failed,
    mark_interview_task_running,
    mark_interview_task_succeeded,
    task_response,
)
from app.services.interviews import InterviewPersistenceService
from app.services.rate_limit import require_api_rate_limit

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


@router.get("/sessions/{session_id}/drafts", response_model=InterviewDraftListResponse)
def list_interview_drafts(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewDraftListResponse:
    """读取当前用户某个面试会话下的全部回答草稿。"""

    session = interview_service.get_owned_session(db=db, current_user=current_user, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")

    valid_question_ids = {question.question_id for question in session.questions}
    drafts = [
        InterviewDraftResponse(
            session_id=session_id,
            question_id=question_id,
            answer=answer,
            expires_in=settings.interview_draft_ttl_seconds,
        )
        for question_id, answer in sorted(get_interview_drafts(session_id=session_id).items())
        if question_id in valid_question_ids
    ]
    return InterviewDraftListResponse(session_id=session_id, drafts=drafts, expires_in=settings.interview_draft_ttl_seconds)


@router.put("/sessions/{session_id}/drafts", response_model=InterviewDraftResponse)
def save_interview_answer_draft(
    session_id: str,
    request: InterviewDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewDraftResponse:
    """保存当前用户某个面试会话下的单题回答草稿。"""

    _require_owned_question(db=db, current_user=current_user, session_id=session_id, question_id=request.question_id)
    save_interview_draft(session_id=session_id, question_id=request.question_id, answer=request.answer)
    return InterviewDraftResponse(
        session_id=session_id,
        question_id=request.question_id,
        answer=request.answer.strip(),
        expires_in=settings.interview_draft_ttl_seconds,
    )


@router.delete("/sessions/{session_id}/drafts/{question_id}", response_model=MessageResponse)
def delete_interview_answer_draft(
    session_id: str,
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """删除当前用户某个面试会话下的单题草稿。"""

    _require_owned_question(db=db, current_user=current_user, session_id=session_id, question_id=question_id)
    delete_interview_draft(session_id=session_id, question_id=question_id)
    return MessageResponse(message="面试草稿已删除")


@router.delete("/sessions/{session_id}/drafts", response_model=MessageResponse)
def clear_interview_answer_drafts(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """清空当前用户某个面试会话下的全部回答草稿。"""

    session = interview_service.get_owned_session(db=db, current_user=current_user, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    clear_interview_drafts(session_id=session_id)
    return MessageResponse(message="面试草稿已清空")


@router.post("/questions", response_model=InterviewSessionResponse)
def generate_questions(
    request: InterviewQuestionRequest,
    current_user: User = Depends(require_api_rate_limit("interviews.questions")),
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
    current_user: User = Depends(require_api_rate_limit("interviews.follow_up")),
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
    current_user: User = Depends(require_api_rate_limit("interviews.follow_up_stream_token")),
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


@router.post("/evaluate/async", response_model=InterviewTaskStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_evaluate_answers(
    request: AnswerSubmissionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_api_rate_limit("interviews.evaluate_async")),
    db: Session = Depends(get_db),
) -> InterviewTaskStatusResponse:
    """提交候选人回答评分任务，返回可轮询的任务状态。"""

    session = interview_service.get_owned_session(db=db, current_user=current_user, session_id=request.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")

    task = create_interview_task(
        task_type="interview.report",
        session_id=request.session_id,
        user_id=current_user.id,
        message="报告评分任务已入队",
    )
    background_tasks.add_task(_run_evaluate_report_task, task.task_id, current_user.id, request, db)
    return task


@router.get("/tasks/{task_id}", response_model=InterviewTaskStatusResponse)
def get_interview_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> InterviewTaskStatusResponse:
    """读取当前用户可见的面试异步任务状态。"""

    payload = get_interview_task(task_id)
    if payload is None or payload.get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task_response(payload)


@router.post("/evaluate", response_model=InterviewReportResponse)
def evaluate_answers(
    request: AnswerSubmissionRequest,
    current_user: User = Depends(require_api_rate_limit("interviews.evaluate")),
    db: Session = Depends(get_db),
) -> InterviewReportResponse:
    """提交候选人回答、生成评分报告，并保存报告快照。"""

    try:
        report = interview_service.evaluate_answers(db=db, current_user=current_user, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    clear_interview_drafts(session_id=request.session_id)
    return interview_service.candidate_report_view(report)


def _run_evaluate_report_task(task_id: str, user_id: int, request: AnswerSubmissionRequest, db: Session) -> None:
    """本地过渡 Worker：执行报告评分并更新任务状态。"""

    try:
        mark_interview_task_running(task_id, message="正在生成评分报告")
        current_user = db.get(User, user_id)
        if current_user is None:
            mark_interview_task_failed(task_id, error="用户不存在")
            return

        report = interview_service.evaluate_answers(db=db, current_user=current_user, request=request)
        if report is None:
            mark_interview_task_failed(task_id, error="面试会话不存在")
            return

        clear_interview_drafts(session_id=request.session_id)
        candidate_report = interview_service.candidate_report_view(report)
        mark_interview_task_succeeded(
            task_id,
            result=candidate_report.model_dump(mode="json"),
            message="评分报告已生成",
        )
    except Exception as exc:  # pragma: no cover - 兜底防止后台任务吞错
        mark_interview_task_failed(task_id, error=str(exc))


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _require_owned_question(db: Session, current_user: User, session_id: str, question_id: str) -> None:
    session = interview_service.get_owned_session(db=db, current_user=current_user, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    if question_id not in {question.question_id for question in session.questions}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="题目不属于该面试会话")
