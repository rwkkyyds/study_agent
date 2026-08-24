"""面试异步任务执行器。

API 的本地 BackgroundTasks 回退和独立 Worker 进程都复用这里，避免两套评分逻辑分叉。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.interview import AnswerSubmissionRequest, InterviewFollowUpRequest, InterviewQuestionRequest
from app.services.interview_drafts import clear_interview_drafts
from app.services.interview_tasks import (
    mark_interview_task_failed,
    mark_interview_task_running,
    mark_interview_task_succeeded,
)
from app.services.interviews import InterviewPersistenceService

interview_service = InterviewPersistenceService()


def run_generate_questions_task(
    task_id: str,
    user_id: int,
    request: InterviewQuestionRequest,
    db: Session,
) -> None:
    """执行面试题生成任务，并更新任务状态。"""

    try:
        mark_interview_task_running(task_id, message="正在生成面试题")
        current_user = db.get(User, user_id)
        if current_user is None:
            mark_interview_task_failed(task_id, error="用户不存在")
            return

        response = interview_service.generate_questions(db=db, current_user=current_user, request=request)
        mark_interview_task_succeeded(
            task_id,
            session_id=response.session_id,
            result=response.model_dump(mode="json"),
            message="面试题已生成",
        )
    except Exception as exc:  # pragma: no cover - Worker/API 任务兜底，具体错误写入任务状态
        mark_interview_task_failed(task_id, error=str(exc))


def run_evaluate_report_task(
    task_id: str,
    user_id: int,
    request: AnswerSubmissionRequest,
    db: Session,
) -> None:
    """执行报告评分任务，并更新任务状态。"""

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
    except Exception as exc:  # pragma: no cover - Worker/API 任务兜底，具体错误写入任务状态
        mark_interview_task_failed(task_id, error=str(exc))


def run_generate_follow_up_task(
    task_id: str,
    user_id: int,
    request: InterviewFollowUpRequest,
    db: Session,
) -> None:
    """执行追问生成任务，并更新任务状态。"""

    try:
        mark_interview_task_running(task_id, message="正在生成追问")
        current_user = db.get(User, user_id)
        if current_user is None:
            mark_interview_task_failed(task_id, error="用户不存在")
            return

        response = interview_service.generate_follow_up(db=db, current_user=current_user, request=request)
        if response is None:
            mark_interview_task_failed(task_id, error="面试会话不存在")
            return

        mark_interview_task_succeeded(
            task_id,
            session_id=request.session_id,
            result=response.model_dump(mode="json"),
            message="追问已生成",
        )
    except Exception as exc:  # pragma: no cover - Worker/API 任务兜底，具体错误写入任务状态
        mark_interview_task_failed(task_id, error=str(exc))
