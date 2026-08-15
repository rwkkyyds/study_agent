"""工单 SSE 事件总线。

Redis 可用时使用 Pub/Sub，保证 Docker 多 worker 下任意进程发布的事件
都能被当前 SSE 连接收到；本地未配置 Redis 时回退到进程内队列。
"""

from __future__ import annotations

import json
import logging
from typing import Any
from dataclasses import dataclass
from queue import Full, Queue
from threading import Lock

from app.core.config import get_settings
from app.models.ticket import Ticket
from app.schemas.ticket import TicketResponse
from app.stability.factory import build_redis_client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TicketEvent:
    """SSE 事件载荷。"""

    event: str
    data: str


@dataclass
class TicketSubscription:
    """单个 SSE 连接的订阅资源。"""

    queue: Queue[TicketEvent]
    channel: str
    pubsub: Any | None = None


class TicketEventBus:
    """按事件频道管理订阅者队列。"""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[Queue[TicketEvent]]] = {}
        self._lock = Lock()
        self._redis = build_redis_client(get_settings().redis_url)

    @staticmethod
    def _channel(ticket_id: int) -> str:
        return f"ticket:{ticket_id}:events"

    @staticmethod
    def _list_channel() -> str:
        return "tickets:events"

    def subscribe(self, ticket_id: int) -> TicketSubscription:
        """订阅某个工单的事件。"""

        return self._subscribe_channel(self._channel(ticket_id))

    def subscribe_list(self) -> TicketSubscription:
        """订阅当前用户可见工单列表的事件。"""

        return self._subscribe_channel(self._list_channel())

    def _subscribe_channel(self, channel: str) -> TicketSubscription:
        """订阅一个 SSE 频道。"""

        queue: Queue[TicketEvent] = Queue(maxsize=100)
        pubsub = None
        if self._redis is not None:
            try:
                pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(channel)
            except Exception as exc:
                logger.warning("ticket_event_redis_subscribe_failed channel=%s error=%s", channel, exc)
                pubsub = None

        with self._lock:
            self._subscribers.setdefault(channel, set()).add(queue)
        return TicketSubscription(queue=queue, channel=channel, pubsub=pubsub)

    def unsubscribe(self, ticket_id: int, subscription: TicketSubscription) -> None:
        """取消订阅，避免断开连接后残留队列。"""

        self._unsubscribe_channel(self._channel(ticket_id), subscription)

    def unsubscribe_list(self, subscription: TicketSubscription) -> None:
        """取消工单列表事件订阅。"""

        self._unsubscribe_channel(self._list_channel(), subscription)

    def _unsubscribe_channel(self, channel: str, subscription: TicketSubscription) -> None:
        """取消订阅一个 SSE 频道。"""

        if subscription.pubsub is not None:
            try:
                subscription.pubsub.unsubscribe(channel)
                subscription.pubsub.close()
            except Exception as exc:
                logger.debug("ticket_event_redis_unsubscribe_failed channel=%s error=%s", channel, exc)

        with self._lock:
            queues = self._subscribers.get(channel)
            if not queues:
                return
            queues.discard(subscription.queue)
            if not queues:
                self._subscribers.pop(channel, None)

    def publish(self, ticket_id: int, event: str, data: str) -> None:
        """向当前订阅该工单的连接广播事件。"""

        self._publish_channel(self._channel(ticket_id), event, data)

    def publish_list(self, event: str, data: str) -> None:
        """向工单列表连接广播事件。"""

        self._publish_channel(self._list_channel(), event, data)

    def _publish_channel(self, channel: str, event: str, data: str) -> None:
        """向当前订阅该频道的连接广播事件。"""

        if self._redis is not None:
            try:
                self._redis.publish(
                    channel,
                    json.dumps({"event": event, "data": data}, ensure_ascii=False),
                )
            except Exception as exc:
                logger.warning("ticket_event_redis_publish_failed channel=%s error=%s", channel, exc)

        with self._lock:
            queues = list(self._subscribers.get(channel, set()))

        for queue in queues:
            try:
                queue.put_nowait(TicketEvent(event=event, data=data))
            except Full:
                try:
                    queue.get_nowait()
                except Exception:
                    pass
                queue.put_nowait(TicketEvent(event=event, data=data))

    def next_event(self, subscription: TicketSubscription, timeout: int = 25) -> TicketEvent | None:
        """阻塞读取下一条事件；Redis 可用时优先读 Pub/Sub。"""

        if subscription.pubsub is not None:
            message = subscription.pubsub.get_message(timeout=timeout)
            if not message:
                return None
            try:
                payload = json.loads(message["data"])
                return TicketEvent(event=payload["event"], data=payload["data"])
            except Exception as exc:
                logger.warning("ticket_event_redis_message_invalid error=%s", exc)
                return None

        try:
            return subscription.queue.get(timeout=timeout)
        except Exception:
            return None


ticket_event_bus = TicketEventBus()


def serialize_ticket(ticket: Ticket) -> str:
    """把 SQLAlchemy 工单对象序列化为前端可直接消费的 JSON。"""

    return TicketResponse.model_validate(ticket).model_dump_json()


def publish_ticket_update(ticket: Ticket) -> None:
    """发布工单快照更新事件。"""

    data = serialize_ticket(ticket)
    ticket_event_bus.publish(
        ticket.id,
        event="ticket.updated",
        data=data,
    )
    ticket_event_bus.publish_list(
        event="ticket.updated",
        data=data,
    )


def publish_ticket_created(ticket: Ticket) -> None:
    """发布新工单创建事件，驱动客服工作台列表实时新增。"""

    data = serialize_ticket(ticket)
    ticket_event_bus.publish(
        ticket.id,
        event="ticket.updated",
        data=data,
    )
    ticket_event_bus.publish_list(
        event="ticket.created",
        data=data,
    )
