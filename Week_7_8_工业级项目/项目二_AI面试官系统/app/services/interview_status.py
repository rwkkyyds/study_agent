"""面试会话状态机定义与兼容转换。"""

SESSION_STATUS_RUNNING = "running"
SESSION_STATUS_EVALUATING = "evaluating"
SESSION_STATUS_AI_REPORTED = "ai_reported"
SESSION_STATUS_REVIEWED = "reviewed"
SESSION_STATUS_ARCHIVED = "archived"

LEGACY_SESSION_STATUS_MAP = {
    "questions_generated": SESSION_STATUS_RUNNING,
    "follow_up_generated": SESSION_STATUS_RUNNING,
    "evaluated": SESSION_STATUS_AI_REPORTED,
}


def normalize_session_status(status: str) -> str:
    """把历史状态映射到阶段八目标状态机。"""

    return LEGACY_SESSION_STATUS_MAP.get(status, status)


def assert_session_can_continue(status: str) -> None:
    """校验当前会话是否仍允许继续生成 AI 内容。"""

    normalized = normalize_session_status(status)
    if normalized in {SESSION_STATUS_REVIEWED, SESSION_STATUS_ARCHIVED}:
        raise ValueError("当前面试状态不允许继续生成 AI 内容")
