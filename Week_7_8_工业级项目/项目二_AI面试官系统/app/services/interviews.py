"""面试持久化服务。"""

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.hiring import CandidateProfile, EvaluationRubric, InterviewBatch, InterviewInvite, Job
from app.models.interview import (
    InterviewAnswer as InterviewAnswerModel,
    InterviewFollowUp,
    InterviewQuestion as InterviewQuestionModel,
    InterviewReport,
    InterviewSession,
)
from app.models.resume import ResumeProfile
from app.models.user import User
from app.schemas.interview import (
    AnswerSubmissionRequest,
    InterviewAnswerRecord,
    InterviewFollowUpRecord,
    InterviewFollowUpRequest,
    InterviewFollowUpResponse,
    InterviewQuestion,
    InterviewQuestionRequest,
    InterviewReportResponse,
    InterviewSessionDetailResponse,
    InterviewSessionListResponse,
    InterviewSessionResponse,
    InterviewSessionSummary,
)
from app.workflow.interview import InterviewWorkflow


@dataclass
class InterviewBusinessContext:
    """一次面试生成请求解析出的招聘业务上下文。"""

    job: Job | None = None
    candidate_profile: CandidateProfile | None = None
    interview_batch: InterviewBatch | None = None
    invite: InterviewInvite | None = None
    rubric: EvaluationRubric | None = None


class InterviewPersistenceService:
    """把图式面试工作流的结果写入数据库。"""

    def __init__(self, workflow: InterviewWorkflow | None = None) -> None:
        self.workflow = workflow or InterviewWorkflow()

    def generate_questions(
        self,
        db: Session,
        current_user: User,
        request: InterviewQuestionRequest,
    ) -> InterviewSessionResponse:
        """生成题目并落库为一次面试会话。"""

        resolved_request, resume_profile, business_context = self._resolve_generation_context(db, current_user, request)
        response = self.workflow.generate_questions(resolved_request)
        response.session_id = self._user_scoped_session_id(db, response.session_id, current_user.id)
        response.job_id = business_context.job.id if business_context.job else None
        response.candidate_profile_id = business_context.candidate_profile.id if business_context.candidate_profile else None
        response.interview_batch_id = business_context.interview_batch.id if business_context.interview_batch else None
        response.invite_id = business_context.invite.id if business_context.invite else None
        response.rubric_id = business_context.rubric.id if business_context.rubric else None

        session = InterviewSession(
            session_id=response.session_id,
            user_id=current_user.id,
            resume_profile_id=resume_profile.id if resume_profile else None,
            job_id=response.job_id,
            candidate_profile_id=response.candidate_profile_id,
            interview_batch_id=response.interview_batch_id,
            invite_id=response.invite_id,
            rubric_id=response.rubric_id,
            resume_text=resolved_request.resume_text or "",
            job_title=response.job_title,
            difficulty=response.difficulty,
            candidate_summary=response.candidate_summary,
            status="running" if business_context.invite else "questions_generated",
        )
        db.add(session)
        db.flush()

        if business_context.invite:
            business_context.invite.status = "accepted"
            business_context.invite.used_at = business_context.invite.used_at or self._utc_now()
        if business_context.candidate_profile:
            business_context.candidate_profile.status = "interviewing"

        db.add_all(
            InterviewQuestionModel(
                session_db_id=session.id,
                question_id=question.id,
                question_type=question.question_type,
                question=question.question,
                expected_points=question.expected_points,
                source=question.source,
            )
            for question in response.questions
        )
        db.commit()
        return response

    def generate_follow_up(
        self,
        db: Session,
        current_user: User,
        request: InterviewFollowUpRequest,
    ) -> InterviewFollowUpResponse | None:
        """校验会话归属，生成多轮追问，并保存追问快照。"""

        session = self._get_user_session(db, current_user, request.session_id)
        if session is None:
            return None

        question_text = next(
            (
                question.question
                for question in session.questions
                if question.question_id == request.question_id
            ),
            "",
        )
        response = self.workflow.generate_follow_up(
            request=request,
            job_title=session.job_title,
            question_text=question_text,
        )
        db.add(
            InterviewFollowUp(
                session_db_id=session.id,
                question_id=request.question_id,
                answer=request.answer,
                follow_up_questions=response.follow_up_questions,
                reason=response.reason,
                workflow_trace=response.workflow_trace,
            )
        )
        session.status = "follow_up_generated"
        db.commit()
        return response

    def evaluate_answers(
        self,
        db: Session,
        current_user: User,
        request: AnswerSubmissionRequest,
    ) -> InterviewReportResponse | None:
        """校验会话归属，生成评分报告，并持久化回答与报告。"""

        session = self._get_user_session(db, current_user, request.session_id)
        if session is None:
            return None

        report = self.workflow.evaluate_answers(
            request,
            rubric_dimensions=session.rubric.dimensions if session.rubric else None,
            rubric_weights=session.rubric.weights if session.rubric else None,
        )
        db.query(InterviewAnswerModel).filter(InterviewAnswerModel.session_db_id == session.id).delete()
        db.query(InterviewReport).filter(InterviewReport.session_db_id == session.id).delete()

        db.add_all(
            InterviewAnswerModel(
                session_db_id=session.id,
                question_id=answer.question_id,
                answer=answer.answer,
            )
            for answer in request.answers
        )
        db.add(
            InterviewReport(
                session_db_id=session.id,
                overall_score=report.overall_score,
                level=report.level,
                dimensions=[dimension.model_dump() for dimension in report.dimensions],
                strengths=report.strengths,
                risks=report.risks,
                follow_up_questions=report.follow_up_questions,
                learning_suggestions=report.learning_suggestions,
            )
        )
        session.status = "evaluated"
        db.commit()
        return report

    def get_owned_session(self, db: Session, current_user: User, session_id: str) -> InterviewSession | None:
        """查询当前用户名下的面试会话，供 API 层做显式归属校验。"""

        return self._get_user_session(db, current_user, session_id)

    def get_owned_session_by_user_id(self, db: Session, user_id: int, session_id: str) -> InterviewSession | None:
        """通过用户 ID 查询归属会话，用于短期 SSE Token 场景。"""

        return (
            db.query(InterviewSession)
            .filter(
                InterviewSession.session_id == session_id,
                InterviewSession.user_id == user_id,
            )
            .first()
        )

    def list_owned_sessions(self, db: Session, current_user: User) -> InterviewSessionListResponse:
        """返回当前用户的历史面试会话摘要。"""

        sessions = (
            db.query(InterviewSession)
            .filter(InterviewSession.user_id == current_user.id)
            .order_by(InterviewSession.created_at.desc(), InterviewSession.id.desc())
            .all()
        )
        return InterviewSessionListResponse(sessions=[self._session_summary(session) for session in sessions])

    def get_owned_session_detail(
        self,
        db: Session,
        current_user: User,
        session_id: str,
    ) -> InterviewSessionDetailResponse | None:
        """返回当前用户某次面试的完整详情。"""

        session = self._get_user_session(db, current_user, session_id)
        if session is None:
            return None

        summary = self._session_summary(session)
        return InterviewSessionDetailResponse(
            **summary.model_dump(),
            resume_text=session.resume_text,
            questions=[
                InterviewQuestion(
                    id=question.question_id,
                    question_type=question.question_type,
                    question=question.question,
                    expected_points=question.expected_points,
                    source=question.source,
                )
                for question in session.questions
            ],
            answers=[
                InterviewAnswerRecord(
                    question_id=answer.question_id,
                    answer=answer.answer,
                    created_at=answer.created_at,
                )
                for answer in session.answers
            ],
            follow_ups=[
                InterviewFollowUpRecord(
                    question_id=follow_up.question_id,
                    answer=follow_up.answer,
                    follow_up_questions=follow_up.follow_up_questions,
                    reason=follow_up.reason,
                    workflow_trace=follow_up.workflow_trace,
                    created_at=follow_up.created_at,
                )
                for follow_up in session.follow_ups
            ],
            report=self._candidate_report_response(session),
        )

    def get_internal_session_report(self, db: Session, session_id: str) -> InterviewReportResponse | None:
        """返回后台复核视角的完整内部评分报告。"""

        session = db.query(InterviewSession).filter(InterviewSession.session_id == session_id).first()
        if session is None:
            return None
        return self._report_response(session)

    @staticmethod
    def _get_user_session(db: Session, current_user: User, session_id: str) -> InterviewSession | None:
        return (
            db.query(InterviewSession)
            .filter(
                InterviewSession.session_id == session_id,
                InterviewSession.user_id == current_user.id,
            )
            .first()
        )

    @staticmethod
    def _resolve_resume_input(
        db: Session,
        current_user: User,
        request: InterviewQuestionRequest,
    ) -> tuple[InterviewQuestionRequest, ResumeProfile | None]:
        if request.resume_profile_id is None:
            if not request.resume_text:
                raise ValueError("必须提供简历文本或候选人画像 ID")
            return request, None

        profile = (
            db.query(ResumeProfile)
            .filter(ResumeProfile.id == request.resume_profile_id, ResumeProfile.user_id == current_user.id)
            .first()
        )
        if profile is None:
            raise ValueError("候选人画像不存在")

        resolved = request.model_copy(update={"resume_text": profile.normalized_text})
        return resolved, profile

    def _resolve_generation_context(
        self,
        db: Session,
        current_user: User,
        request: InterviewQuestionRequest,
    ) -> tuple[InterviewQuestionRequest, ResumeProfile | None, InterviewBusinessContext]:
        business_context = self._resolve_business_context(db, current_user, request)
        request_updates: dict[str, object] = {}

        if business_context.job:
            request_updates["job_title"] = business_context.job.title
        elif not request.job_title:
            raise ValueError("必须提供岗位名称、岗位 ID 或有效面试邀请")

        if (
            business_context.candidate_profile
            and business_context.candidate_profile.resume_profile_id
            and request.resume_profile_id is None
            and not request.resume_text
        ):
            request_updates["resume_profile_id"] = business_context.candidate_profile.resume_profile_id

        resolved_request = request.model_copy(update=request_updates) if request_updates else request
        resolved_request, resume_profile = self._resolve_resume_input(db, current_user, resolved_request)
        return resolved_request, resume_profile, business_context

    def _resolve_business_context(
        self,
        db: Session,
        current_user: User,
        request: InterviewQuestionRequest,
    ) -> InterviewBusinessContext:
        invite = self._resolve_invite(db, current_user, request.invite_token) if request.invite_token else None
        job = invite.job if invite else self._resolve_job(db, request.job_id)
        candidate_profile = invite.candidate_profile if invite else self._resolve_candidate_profile(db, current_user, request.candidate_profile_id)
        interview_batch = invite.batch if invite else self._resolve_interview_batch(db, request.interview_batch_id)

        if interview_batch and job and interview_batch.job_id != job.id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="批次不属于该岗位")

        if invite and candidate_profile:
            self._bind_invited_candidate_to_user(current_user, candidate_profile)

        rubric = self._resolve_rubric(db, request.rubric_id, job)

        return InterviewBusinessContext(
            job=job,
            candidate_profile=candidate_profile,
            interview_batch=interview_batch,
            invite=invite,
            rubric=rubric,
        )

    def _resolve_invite(self, db: Session, current_user: User, invite_token: str) -> InterviewInvite:
        invite = db.query(InterviewInvite).filter(InterviewInvite.invite_token == invite_token).first()
        if invite is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试邀请不存在")

        if db.query(InterviewSession.id).filter(InterviewSession.invite_id == invite.id).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="面试邀请已创建会话，请从历史会话继续")

        if self._as_aware_datetime(invite.expires_at) <= self._utc_now():
            invite.status = "expired"
            db.commit()
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="面试邀请已过期")

        if invite.status not in {"invited", "accepted"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="面试邀请状态不允许开始面试")

        candidate_profile = invite.candidate_profile
        if candidate_profile and current_user.role == "candidate" and candidate_profile.user_id not in {None, current_user.id}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="面试邀请不属于当前用户")

        return invite

    @staticmethod
    def _resolve_job(db: Session, job_id: int | None) -> Job | None:
        if job_id is None:
            return None
        job = db.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
        return job

    @staticmethod
    def _resolve_candidate_profile(db: Session, current_user: User, candidate_profile_id: int | None) -> CandidateProfile | None:
        if candidate_profile_id is None:
            return None
        candidate_profile = db.get(CandidateProfile, candidate_profile_id)
        if candidate_profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="候选人档案不存在")
        if current_user.role == "candidate" and candidate_profile.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="候选人档案不属于当前用户")
        return candidate_profile

    @staticmethod
    def _resolve_interview_batch(db: Session, interview_batch_id: int | None) -> InterviewBatch | None:
        if interview_batch_id is None:
            return None
        interview_batch = db.get(InterviewBatch, interview_batch_id)
        if interview_batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="招聘批次不存在")
        return interview_batch

    @staticmethod
    def _resolve_rubric(db: Session, rubric_id: int | None, job: Job | None) -> EvaluationRubric | None:
        if rubric_id is not None:
            rubric = db.get(EvaluationRubric, rubric_id)
            if rubric is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评分标准不存在")
            if job and rubric.job_id != job.id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="评分标准不属于该岗位")
            return rubric

        if job is None:
            return None
        return (
            db.query(EvaluationRubric)
            .filter(EvaluationRubric.job_id == job.id, EvaluationRubric.is_active.is_(True))
            .order_by(EvaluationRubric.created_at.desc(), EvaluationRubric.id.desc())
            .first()
        )

    @staticmethod
    def _bind_invited_candidate_to_user(current_user: User, candidate_profile: CandidateProfile) -> None:
        if current_user.role != "candidate":
            return
        if candidate_profile.user_id is None:
            candidate_profile.user_id = current_user.id

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _as_aware_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @staticmethod
    def _user_scoped_session_id(db: Session, base_session_id: str, user_id: int) -> str:
        """生成可读且唯一的用户级面试会话 ID。"""

        session_id = f"{base_session_id}-u{user_id}"
        if not db.query(InterviewSession.id).filter(InterviewSession.session_id == session_id).first():
            return session_id

        suffix = 2
        while db.query(InterviewSession.id).filter(InterviewSession.session_id == f"{session_id}-{suffix}").first():
            suffix += 1
        return f"{session_id}-{suffix}"

    @staticmethod
    def _session_summary(session: InterviewSession) -> InterviewSessionSummary:
        report = session.report
        return InterviewSessionSummary(
            session_id=session.session_id,
            job_title=session.job_title,
            difficulty=session.difficulty,
            status=session.status,
            candidate_summary=session.candidate_summary,
            question_count=len(session.questions),
            answer_count=len(session.answers),
            follow_up_count=len(session.follow_ups),
            overall_score=report.overall_score if report else None,
            level=report.level if report else None,
            job_id=session.job_id,
            candidate_profile_id=session.candidate_profile_id,
            interview_batch_id=session.interview_batch_id,
            invite_id=session.invite_id,
            rubric_id=session.rubric_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    @staticmethod
    def _report_response(session: InterviewSession) -> InterviewReportResponse | None:
        report = session.report
        if report is None:
            return None
        return InterviewReportResponse(
            session_id=session.session_id,
            overall_score=report.overall_score,
            level=report.level,
            visibility="internal",
            dimensions=report.dimensions,
            strengths=report.strengths,
            risks=report.risks,
            follow_up_questions=report.follow_up_questions,
            learning_suggestions=report.learning_suggestions,
            workflow_trace=[],
        )

    @classmethod
    def _candidate_report_response(cls, session: InterviewSession) -> InterviewReportResponse | None:
        report = cls._report_response(session)
        if report is None:
            return None
        return cls.candidate_report_view(report)

    @staticmethod
    def candidate_report_view(report: InterviewReportResponse) -> InterviewReportResponse:
        """候选人视角报告：保留结论和建议，隐藏内部维度分和风险标记。"""

        return report.model_copy(
            update={
                "visibility": "candidate",
                "dimensions": [],
                "risks": [],
            }
        )
