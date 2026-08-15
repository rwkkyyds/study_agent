"""工单查询与处理 API。

提供客服工作台工单列表，以及聊天转人工所需的单工单详情查询。
权限规则：
- customer：不进入工单工作台，只能在聊天页查看/补充自己的转人工会话
- agent：可以查看 open 待接入工单和自己已领取的工单
- admin：可以查看全部工单
- agent/admin：可领取、回复、解决和关闭工单
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ticket import Message, Ticket
from app.models.user import User
from app.schemas.ticket import TicketReplyRequest, TicketResponse
from app.services.auth import get_current_user, require_any_role
from app.services.ticket_events import (
    publish_ticket_update,
    serialize_ticket,
    ticket_event_bus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _can_view_ticket(ticket: Ticket, current_user: User) -> bool:
    """判断当前用户是否可查看工单。"""

    if current_user.role == "admin":
        return True
    if current_user.role == "customer":
        return ticket.customer_id == current_user.id
    if current_user.role == "agent":
        return ticket.status == "open" or ticket.agent_id == current_user.id
    return False


def _can_view_ticket_payload(ticket: dict, current_user: User) -> bool:
    """判断当前客服/管理员是否可接收列表 SSE 中的工单快照。"""

    if current_user.role == "admin":
        return True
    if current_user.role == "customer":
        return ticket.get("customer_id") == current_user.id
    if current_user.role == "agent":
        return ticket.get("status") == "open" or ticket.get("agent_id") == current_user.id
    return False


def _ensure_can_view_ticket(ticket: Ticket, current_user: User) -> None:
    if not _can_view_ticket(ticket, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看该工单",
        )


def _ensure_can_handle_ticket(ticket: Ticket, current_user: User) -> None:
    """客服处理权限：admin 可处理全部，agent 可处理 open 或自己领取的工单。"""

    if current_user.role == "admin":
        return
    if current_user.role == "agent" and (ticket.status == "open" or ticket.agent_id == current_user.id):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="无权处理该工单",
    )


def _format_sse(event: str, data: str) -> str:
    """格式化 SSE 事件，兼容多行 data。"""

    lines = [f"event: {event}"]
    lines.extend(f"data: {line}" for line in data.splitlines())
    return "\n".join(lines) + "\n\n"


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_any_role("agent", "admin")),
    db: Session = Depends(get_db),
) -> list[Ticket]:
    """列出客服工作台可见的工单。

    - agent：看 open 待处理工单和自己已领取的工单
    - admin：看全部工单
    """

    query = db.query(Ticket).order_by(Ticket.created_at.desc())
    if current_user.role == "agent":
        query = query.filter(or_(Ticket.status == "open", Ticket.agent_id == current_user.id))
    return query.offset(skip).limit(limit).all()


@router.get("/events")
async def stream_ticket_list_events(
    request: Request,
    current_user: User = Depends(require_any_role("agent", "admin")),
) -> StreamingResponse:
    """SSE 推送当前用户可见的工单列表变化，替代手动刷新列表。"""

    subscription = ticket_event_bus.subscribe_list()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                event = await asyncio.to_thread(ticket_event_bus.next_event, subscription, 25)
                if event is None:
                    yield ": keep-alive\n\n"
                    continue

                try:
                    ticket = json.loads(event.data)
                except json.JSONDecodeError as exc:
                    logger.warning("ticket_list_event_payload_invalid error=%s", exc)
                    continue

                if _can_view_ticket_payload(ticket, current_user):
                    yield _format_sse(event.event, event.data)
        finally:
            ticket_event_bus.unsubscribe_list(subscription)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Ticket:
    """获取单个工单详情（含消息记录）。

    customer 只能访问自己的工单，agent 可访问 open 或自己领取的工单，admin 可访问任意工单。
    """

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在",
        )
    _ensure_can_view_ticket(ticket, current_user)
    return ticket


@router.get("/{ticket_id}/events")
async def stream_ticket_events(
    ticket_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """SSE 推送单个转人工会话变化，供客服工作台和用户聊天页共用。"""

    ticket = _get_ticket_or_404(ticket_id, db)
    _ensure_can_view_ticket(ticket, current_user)
    subscription = ticket_event_bus.subscribe(ticket_id)
    snapshot = serialize_ticket(ticket)

    async def event_generator():
        yield _format_sse("ticket.snapshot", snapshot)
        try:
            while True:
                if await request.is_disconnected():
                    break
                event = await asyncio.to_thread(ticket_event_bus.next_event, subscription, 25)
                if event is None:
                    yield ": keep-alive\n\n"
                    continue
                yield _format_sse(event.event, event.data)
        finally:
            ticket_event_bus.unsubscribe(ticket_id, subscription)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _get_ticket_or_404(ticket_id: int, db: Session) -> Ticket:
    """按 ID 查找工单，不存在则返回 404。"""

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在",
        )
    return ticket


@router.post("/{ticket_id}/claim", response_model=TicketResponse)
def claim_ticket(
    ticket_id: int,
    current_user: User = Depends(require_any_role("agent", "admin")),
    db: Session = Depends(get_db),
) -> Ticket:
    """客服/管理员领取工单（open → assigned），记录处理人。"""

    ticket = _get_ticket_or_404(ticket_id, db)
    _ensure_can_handle_ticket(ticket, current_user)
    if ticket.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"工单当前状态为 {ticket.status}，仅 open 状态可领取",
        )
    ticket.status = "assigned"
    ticket.agent_id = current_user.id
    db.add(Message(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        sender_role="system",
        content=f"工单已被客服领取，正在处理中。",
        msg_type="system",
    ))
    db.commit()
    db.refresh(ticket)
    publish_ticket_update(ticket)
    logger.info("工单已领取 ticket_id=%d agent_id=%d", ticket.id, current_user.id)
    return ticket


@router.post("/{ticket_id}/reply", response_model=TicketResponse)
def reply_ticket(
    ticket_id: int,
    request: TicketReplyRequest,
    current_user: User = Depends(require_any_role("agent", "admin")),
    db: Session = Depends(get_db),
) -> Ticket:
    """客服回复工单，追加一条 agent 消息。"""

    ticket = _get_ticket_or_404(ticket_id, db)
    _ensure_can_handle_ticket(ticket, current_user)
    if ticket.status in ("closed",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="工单已关闭，无法回复",
        )
    db.add(Message(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        sender_role="agent",
        content=request.content.strip(),
        msg_type="text",
    ))
    # 若工单仍为 open，回复视同领取
    if ticket.status == "open":
        ticket.status = "assigned"
        ticket.agent_id = current_user.id
    db.commit()
    db.refresh(ticket)
    publish_ticket_update(ticket)
    logger.info("工单已回复 ticket_id=%d agent_id=%d", ticket.id, current_user.id)
    return ticket


@router.post("/{ticket_id}/messages", response_model=TicketResponse)
def append_customer_message(
    ticket_id: int,
    request: TicketReplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Ticket:
    """用户在转人工后的同一聊天窗口继续发送消息。"""

    ticket = _get_ticket_or_404(ticket_id, db)
    if current_user.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="客服/管理员请使用客服工作台回复用户",
        )
    if ticket.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权回复该工单",
        )
    if ticket.status in ("resolved", "closed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"工单当前状态为 {ticket.status}，无法继续发送消息",
        )
    db.add(Message(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        sender_role="customer",
        content=request.content.strip(),
        msg_type="text",
    ))
    db.commit()
    db.refresh(ticket)
    publish_ticket_update(ticket)
    logger.info("用户追加工单消息 ticket_id=%d user_id=%d", ticket.id, current_user.id)
    return ticket


@router.post("/{ticket_id}/resolve", response_model=TicketResponse)
def resolve_ticket(
    ticket_id: int,
    current_user: User = Depends(require_any_role("agent", "admin")),
    db: Session = Depends(get_db),
) -> Ticket:
    """客服标记工单已解决（assigned → resolved）。"""

    ticket = _get_ticket_or_404(ticket_id, db)
    _ensure_can_handle_ticket(ticket, current_user)
    if ticket.status != "assigned":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"工单当前状态为 {ticket.status}，仅 assigned 状态可标记解决",
        )
    ticket.status = "resolved"
    db.add(Message(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        sender_role="system",
        content="工单已标记为解决。",
        msg_type="system",
    ))
    db.commit()
    db.refresh(ticket)
    publish_ticket_update(ticket)
    logger.info("工单已解决 ticket_id=%d agent_id=%d", ticket.id, current_user.id)
    return ticket


@router.post("/{ticket_id}/close", response_model=TicketResponse)
def close_ticket(
    ticket_id: int,
    current_user: User = Depends(require_any_role("agent", "admin")),
    db: Session = Depends(get_db),
) -> Ticket:
    """客服关闭工单（resolved → closed）。"""

    ticket = _get_ticket_or_404(ticket_id, db)
    _ensure_can_handle_ticket(ticket, current_user)
    if ticket.status != "resolved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"工单当前状态为 {ticket.status}，仅 resolved 状态可关闭",
        )
    ticket.status = "closed"
    db.add(Message(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        sender_role="system",
        content="工单已关闭。感谢您的反馈。",
        msg_type="system",
    ))
    db.commit()
    db.refresh(ticket)
    publish_ticket_update(ticket)
    logger.info("工单已关闭 ticket_id=%d agent_id=%d", ticket.id, current_user.id)
    return ticket
