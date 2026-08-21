"""AI 面试业务接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.interview import (
    AnswerSubmissionRequest,
    InterviewFollowUpRequest,
    InterviewFollowUpResponse,
    InterviewQuestionRequest,
    InterviewReportResponse,
    InterviewSessionResponse,
)
from app.services.auth import get_current_user
from app.services.interviews import InterviewPersistenceService

router = APIRouter(prefix="/interviews", tags=["interviews"])
interview_service = InterviewPersistenceService()


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
