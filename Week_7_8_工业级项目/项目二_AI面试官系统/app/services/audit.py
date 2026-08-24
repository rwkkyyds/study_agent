"""审计日志服务。"""

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.security import AuditLog


def record_audit_log(
    db: Session,
    *,
    action: str,
    status: str,
    actor_user_id: int | None = None,
    username: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    request: Request | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    """记录关键操作审计日志。"""

    audit_log = AuditLog(
        action=action,
        status=status,
        actor_user_id=actor_user_id,
        username=username,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        detail=detail,
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log
