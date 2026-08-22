"""面试持久化服务。"""

from sqlalchemy.orm import Session

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

        resolved_request, resume_profile = self._resolve_resume_input(db, current_user, request)
        response = self.workflow.generate_questions(resolved_request)
        response.session_id = self._user_scoped_session_id(db, response.session_id, current_user.id)

        session = InterviewSession(
            session_id=response.session_id,
            user_id=current_user.id,
            resume_profile_id=resume_profile.id if resume_profile else None,
            resume_text=resolved_request.resume_text or "",
            job_title=response.job_title,
            difficulty=response.difficulty,
            candidate_summary=response.candidate_summary,
            status="questions_generated",
        )
        db.add(session)
        db.flush()

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

        response = self.workflow.generate_follow_up(request=request, job_title=session.job_title)
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

        report = self.workflow.evaluate_answers(request)
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
            report=self._report_response(session),
        )

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
            dimensions=report.dimensions,
            strengths=report.strengths,
            risks=report.risks,
            follow_up_questions=report.follow_up_questions,
            learning_suggestions=report.learning_suggestions,
            workflow_trace=[],
        )
