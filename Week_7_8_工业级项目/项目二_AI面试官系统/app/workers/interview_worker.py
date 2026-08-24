"""Redis 队列版面试 Worker。

运行方式：
    python -m app.workers.interview_worker
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import ContextManager

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.schemas.interview import AnswerSubmissionRequest, InterviewFollowUpRequest, InterviewQuestionRequest
from app.services.interview_task_runner import run_evaluate_report_task, run_generate_follow_up_task, run_generate_questions_task
from app.services.interview_tasks import (
    dequeue_interview_task_job,
    interview_worker_queue_status,
    mark_interview_task_failed,
)

logger = logging.getLogger(__name__)


def run_once(
    *,
    timeout_seconds: int | None = None,
    db_factory: Callable[[], ContextManager[Session]] = SessionLocal,
) -> bool:
    """消费并执行一个任务；没有任务时返回 False。"""

    job = dequeue_interview_task_job(timeout_seconds=timeout_seconds)
    if job is None:
        return False

    task_type = job.get("task_type")
    with db_factory() as db:
        if task_type == "interview.questions":
            run_generate_questions_task(
                task_id=job["task_id"],
                user_id=int(job["user_id"]),
                request=InterviewQuestionRequest.model_validate(job["request"]),
                db=db,
            )
        elif task_type == "interview.follow_up":
            run_generate_follow_up_task(
                task_id=job["task_id"],
                user_id=int(job["user_id"]),
                request=InterviewFollowUpRequest.model_validate(job["request"]),
                db=db,
            )
        elif task_type == "interview.report":
            run_evaluate_report_task(
                task_id=job["task_id"],
                user_id=int(job["user_id"]),
                request=AnswerSubmissionRequest.model_validate(job["request"]),
                db=db,
            )
        else:
            logger.warning("忽略未知任务类型: %s", task_type)
            mark_interview_task_failed(job["task_id"], error=f"未知任务类型: {task_type}")
    return True


def main() -> None:
    """持续消费 Redis 队列。"""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    queue_status = interview_worker_queue_status()
    if queue_status["status"] != "enabled":
        raise RuntimeError(f"interview worker queue 未启用: {queue_status}")

    logger.info("interview worker started: backend=%s queue=%s", queue_status["backend"], queue_status["queue"])
    while True:
        run_once()


if __name__ == "__main__":
    main()
