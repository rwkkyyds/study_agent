"""招聘业务域服务。"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.hiring import (
    CandidateProfile,
    EvaluationRubric,
    InterviewBatch,
    InterviewInvite,
    Job,
    ManualReview,
    NotificationLog,
)
from app.models.interview import InterviewSession
from app.models.resume import ResumeProfile
from app.models.user import User
from app.schemas.hiring import (
    CandidateProfileCreateRequest,
    EvaluationRubricCreateRequest,
    InterviewBatchCreateRequest,
    InterviewInviteCreateRequest,
    JobCreateRequest,
    ManualReviewCreateRequest,
)
from app.services.audit import record_audit_log


class HiringDomainService:
    """岗位、候选人、批次、邀请、评分标准和人工复核的最小业务服务。"""

    def create_job(self, db: Session, current_user: User, payload: JobCreateRequest, request: Request) -> Job:
        job = Job(
            title=payload.title,
            level=payload.level,
            department=payload.department,
            jd_text=payload.jd_text,
            skill_requirements=payload.skill_requirements,
            scoring_dimensions=payload.scoring_dimensions,
            status=payload.status,
            created_by_user_id=current_user.id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        self._audit(db, current_user, "hiring.job.create", "job", job.id, request)
        return job

    def list_jobs(self, db: Session) -> list[Job]:
        return db.query(Job).order_by(Job.created_at.desc(), Job.id.desc()).all()

    def create_candidate_profile(
        self,
        db: Session,
        current_user: User,
        payload: CandidateProfileCreateRequest,
        request: Request,
    ) -> CandidateProfile:
        if payload.user_id is not None and db.get(User, payload.user_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="候选人用户不存在")
        if payload.resume_profile_id is not None and db.get(ResumeProfile, payload.resume_profile_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历画像不存在")

        candidate = CandidateProfile(
            user_id=payload.user_id,
            resume_profile_id=payload.resume_profile_id,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            source=payload.source,
            tags=payload.tags,
            status=payload.status,
            created_by_user_id=current_user.id,
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        self._audit(db, current_user, "hiring.candidate.create", "candidate_profile", candidate.id, request)
        return candidate

    def list_candidate_profiles(self, db: Session) -> list[CandidateProfile]:
        return db.query(CandidateProfile).order_by(CandidateProfile.created_at.desc(), CandidateProfile.id.desc()).all()

    def create_batch(
        self,
        db: Session,
        current_user: User,
        payload: InterviewBatchCreateRequest,
        request: Request,
    ) -> InterviewBatch:
        self._require_job(db, payload.job_id)
        batch = InterviewBatch(
            job_id=payload.job_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            created_by_user_id=current_user.id,
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        self._audit(db, current_user, "hiring.batch.create", "interview_batch", batch.id, request)
        return batch

    def list_batches(self, db: Session) -> list[InterviewBatch]:
        return db.query(InterviewBatch).order_by(InterviewBatch.created_at.desc(), InterviewBatch.id.desc()).all()

    def create_invite(
        self,
        db: Session,
        current_user: User,
        payload: InterviewInviteCreateRequest,
        request: Request,
    ) -> InterviewInvite:
        self._require_job(db, payload.job_id)
        candidate = self._require_candidate(db, payload.candidate_profile_id)
        if payload.batch_id is not None:
            batch = self._require_batch(db, payload.batch_id)
            if batch.job_id != payload.job_id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="批次不属于该岗位")

        invite = InterviewInvite(
            invite_token=self._unique_invite_token(db),
            job_id=payload.job_id,
            candidate_profile_id=payload.candidate_profile_id,
            batch_id=payload.batch_id,
            expires_at=payload.expires_at or datetime.now(timezone.utc) + timedelta(days=7),
            created_by_user_id=current_user.id,
        )
        db.add(invite)
        db.flush()
        db.add(
            NotificationLog(
                invite_id=invite.id,
                candidate_profile_id=candidate.id,
                channel="in_app",
                recipient=candidate.email or candidate.full_name,
                template_key="interview_invite_created",
                status="queued",
                payload={"invite_token": invite.invite_token, "job_id": invite.job_id},
            )
        )
        db.commit()
        db.refresh(invite)
        self._audit(db, current_user, "hiring.invite.create", "interview_invite", invite.id, request)
        return invite

    def list_invites(self, db: Session) -> list[InterviewInvite]:
        return db.query(InterviewInvite).order_by(InterviewInvite.created_at.desc(), InterviewInvite.id.desc()).all()

    def get_invite_by_token(self, db: Session, invite_token: str) -> InterviewInvite | None:
        return db.query(InterviewInvite).filter(InterviewInvite.invite_token == invite_token).first()

    def create_rubric(
        self,
        db: Session,
        current_user: User,
        payload: EvaluationRubricCreateRequest,
        request: Request,
    ) -> EvaluationRubric:
        self._require_job(db, payload.job_id)
        rubric = EvaluationRubric(
            job_id=payload.job_id,
            version=payload.version,
            name=payload.name,
            dimensions=payload.dimensions,
            weights=payload.weights,
            is_active=payload.is_active,
            created_by_user_id=current_user.id,
        )
        db.add(rubric)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该岗位下评分标准版本已存在") from exc
        db.refresh(rubric)
        self._audit(db, current_user, "hiring.rubric.create", "evaluation_rubric", rubric.id, request)
        return rubric

    def list_rubrics(self, db: Session) -> list[EvaluationRubric]:
        return db.query(EvaluationRubric).order_by(EvaluationRubric.created_at.desc(), EvaluationRubric.id.desc()).all()

    def create_manual_review(
        self,
        db: Session,
        current_user: User,
        payload: ManualReviewCreateRequest,
        request: Request,
    ) -> ManualReview:
        session = (
            db.query(InterviewSession)
            .filter(InterviewSession.session_id == payload.session_id)
            .first()
        )
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")

        review = ManualReview(
            session_db_id=session.id,
            reviewer_user_id=current_user.id,
            recommendation=payload.recommendation,
            decision=payload.decision,
            score_override=payload.score_override,
            comments=payload.comments,
            risk_flags=payload.risk_flags,
        )
        db.add(review)
        session.status = "reviewed"
        db.commit()
        db.refresh(review)
        self._audit(db, current_user, "hiring.manual_review.create", "manual_review", review.id, request)
        return review

    def list_manual_reviews(self, db: Session, session_id: str | None = None) -> list[ManualReview]:
        query = db.query(ManualReview).join(InterviewSession)
        if session_id:
            query = query.filter(InterviewSession.session_id == session_id)
        return query.order_by(ManualReview.created_at.desc(), ManualReview.id.desc()).all()

    def list_notification_logs(self, db: Session) -> list[NotificationLog]:
        return db.query(NotificationLog).order_by(NotificationLog.created_at.desc(), NotificationLog.id.desc()).all()

    @staticmethod
    def _require_job(db: Session, job_id: int) -> Job:
        job = db.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
        return job

    @staticmethod
    def _require_candidate(db: Session, candidate_profile_id: int) -> CandidateProfile:
        candidate = db.get(CandidateProfile, candidate_profile_id)
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="候选人档案不存在")
        return candidate

    @staticmethod
    def _require_batch(db: Session, batch_id: int) -> InterviewBatch:
        batch = db.get(InterviewBatch, batch_id)
        if batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
        return batch

    @staticmethod
    def _unique_invite_token(db: Session) -> str:
        token = secrets.token_urlsafe(32)
        while db.query(InterviewInvite.id).filter(InterviewInvite.invite_token == token).first():
            token = secrets.token_urlsafe(32)
        return token

    @staticmethod
    def _audit(
        db: Session,
        current_user: User,
        action: str,
        resource_type: str,
        resource_id: int,
        request: Request,
    ) -> None:
        record_audit_log(
            db,
            action=action,
            status="success",
            actor_user_id=current_user.id,
            username=current_user.username,
            resource_type=resource_type,
            resource_id=str(resource_id),
            request=request,
        )
