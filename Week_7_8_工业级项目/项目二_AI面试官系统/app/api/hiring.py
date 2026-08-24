"""招聘业务域 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.hiring import (
    CandidateProfileCreateRequest,
    CandidateProfileResponse,
    EvaluationRubricCreateRequest,
    EvaluationRubricResponse,
    InterviewBatchCreateRequest,
    InterviewBatchResponse,
    InterviewInviteCreateRequest,
    InterviewInviteResponse,
    JobCreateRequest,
    JobResponse,
    ManualReviewCreateRequest,
    ManualReviewResponse,
    NotificationLogResponse,
)
from app.schemas.interview import InterviewReportResponse
from app.services.auth import require_any_role
from app.services.hiring import HiringDomainService
from app.services.interviews import InterviewPersistenceService

router = APIRouter(prefix="/hiring", tags=["hiring"])
hiring_service = HiringDomainService()
interview_service = InterviewPersistenceService()

HR_MANAGER_ROLES = ("hr", "admin")
REVIEWER_ROLES = ("interviewer", "hr", "admin")


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreateRequest,
    request: Request,
    current_user: User = Depends(require_any_role(*HR_MANAGER_ROLES)),
    db: Session = Depends(get_db),
) -> JobResponse:
    """HR/Admin 创建岗位。"""

    return hiring_service.create_job(db=db, current_user=current_user, payload=payload, request=request)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(
    current_user: User = Depends(require_any_role(*REVIEWER_ROLES)),
    db: Session = Depends(get_db),
) -> list[JobResponse]:
    """Interviewer/HR/Admin 查看岗位列表。"""

    return hiring_service.list_jobs(db)


@router.post("/candidates", response_model=CandidateProfileResponse, status_code=status.HTTP_201_CREATED)
def create_candidate_profile(
    payload: CandidateProfileCreateRequest,
    request: Request,
    current_user: User = Depends(require_any_role(*HR_MANAGER_ROLES)),
    db: Session = Depends(get_db),
) -> CandidateProfileResponse:
    """HR/Admin 创建候选人档案。"""

    return hiring_service.create_candidate_profile(db=db, current_user=current_user, payload=payload, request=request)


@router.get("/candidates", response_model=list[CandidateProfileResponse])
def list_candidate_profiles(
    current_user: User = Depends(require_any_role(*REVIEWER_ROLES)),
    db: Session = Depends(get_db),
) -> list[CandidateProfileResponse]:
    """Interviewer/HR/Admin 查看候选人档案。"""

    return hiring_service.list_candidate_profiles(db)


@router.post("/batches", response_model=InterviewBatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: InterviewBatchCreateRequest,
    request: Request,
    current_user: User = Depends(require_any_role(*HR_MANAGER_ROLES)),
    db: Session = Depends(get_db),
) -> InterviewBatchResponse:
    """HR/Admin 创建招聘批次。"""

    return hiring_service.create_batch(db=db, current_user=current_user, payload=payload, request=request)


@router.get("/batches", response_model=list[InterviewBatchResponse])
def list_batches(
    current_user: User = Depends(require_any_role(*REVIEWER_ROLES)),
    db: Session = Depends(get_db),
) -> list[InterviewBatchResponse]:
    """Interviewer/HR/Admin 查看招聘批次。"""

    return hiring_service.list_batches(db)


@router.post("/invites", response_model=InterviewInviteResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: InterviewInviteCreateRequest,
    request: Request,
    current_user: User = Depends(require_any_role(*HR_MANAGER_ROLES)),
    db: Session = Depends(get_db),
) -> InterviewInviteResponse:
    """HR/Admin 创建面试邀请，并写入待发送通知日志。"""

    return hiring_service.create_invite(db=db, current_user=current_user, payload=payload, request=request)


@router.get("/invites", response_model=list[InterviewInviteResponse])
def list_invites(
    current_user: User = Depends(require_any_role(*HR_MANAGER_ROLES)),
    db: Session = Depends(get_db),
) -> list[InterviewInviteResponse]:
    """HR/Admin 查看邀请列表。"""

    return hiring_service.list_invites(db)


@router.get("/invites/{invite_token}", response_model=InterviewInviteResponse)
def get_invite(invite_token: str, db: Session = Depends(get_db)) -> InterviewInviteResponse:
    """公开邀请查询入口，供候选人门户通过 token 获取邀请。"""

    invite = hiring_service.get_invite_by_token(db=db, invite_token=invite_token)
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试邀请不存在")
    return invite


@router.post("/rubrics", response_model=EvaluationRubricResponse, status_code=status.HTTP_201_CREATED)
def create_rubric(
    payload: EvaluationRubricCreateRequest,
    request: Request,
    current_user: User = Depends(require_any_role(*HR_MANAGER_ROLES)),
    db: Session = Depends(get_db),
) -> EvaluationRubricResponse:
    """HR/Admin 创建岗位评分标准版本。"""

    return hiring_service.create_rubric(db=db, current_user=current_user, payload=payload, request=request)


@router.get("/rubrics", response_model=list[EvaluationRubricResponse])
def list_rubrics(
    current_user: User = Depends(require_any_role(*REVIEWER_ROLES)),
    db: Session = Depends(get_db),
) -> list[EvaluationRubricResponse]:
    """Interviewer/HR/Admin 查看评分标准。"""

    return hiring_service.list_rubrics(db)


@router.post("/manual-reviews", response_model=ManualReviewResponse, status_code=status.HTTP_201_CREATED)
def create_manual_review(
    payload: ManualReviewCreateRequest,
    request: Request,
    current_user: User = Depends(require_any_role(*REVIEWER_ROLES)),
    db: Session = Depends(get_db),
) -> ManualReviewResponse:
    """Interviewer/HR/Admin 创建人工复核。"""

    return hiring_service.create_manual_review(db=db, current_user=current_user, payload=payload, request=request)


@router.get("/manual-reviews", response_model=list[ManualReviewResponse])
def list_manual_reviews(
    session_id: str | None = Query(default=None),
    current_user: User = Depends(require_any_role(*REVIEWER_ROLES)),
    db: Session = Depends(get_db),
) -> list[ManualReviewResponse]:
    """Interviewer/HR/Admin 查看人工复核列表，可按面试会话过滤。"""

    return hiring_service.list_manual_reviews(db=db, session_id=session_id)


@router.get("/interview-sessions/{session_id}/report", response_model=InterviewReportResponse)
def get_internal_interview_report(
    session_id: str,
    current_user: User = Depends(require_any_role(*REVIEWER_ROLES)),
    db: Session = Depends(get_db),
) -> InterviewReportResponse:
    """Interviewer/HR/Admin 查看完整内部评分报告。"""

    report = interview_service.get_internal_session_report(db=db, session_id=session_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试报告不存在")
    return report


@router.get("/notification-logs", response_model=list[NotificationLogResponse])
def list_notification_logs(
    current_user: User = Depends(require_any_role(*HR_MANAGER_ROLES)),
    db: Session = Depends(get_db),
) -> list[NotificationLogResponse]:
    """HR/Admin 查看通知日志。"""

    return hiring_service.list_notification_logs(db)
