"""工单查询 API 测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db
from app.main import app
from app.models.ticket import Message, Ticket
from app.services.auth import get_current_user

# 使用独立的测试数据库
TEST_DATABASE_URL = "sqlite:///./test_tickets.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试函数重建表，保证隔离。"""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


def _make_user_stub(user_id: int = 1, role: str = "customer"):
    """创建用户桩，用于覆盖 get_current_user 依赖。"""
    return type("UserStub", (), {"id": user_id, "role": role, "is_active": True})()


class TestTickets:
    """工单查询 API 测试集。"""

    LIST_URL = "/tickets"

    def _create_ticket(
        self,
        db,
        customer_id: int = 1,
        title: str = "测试工单",
        status: str = "open",
        agent_id: int | None = None,
    ) -> int:
        """直接向测试数据库写入一条工单，返回工单 ID。"""
        ticket = Ticket(
            title=title,
            description="工单描述",
            status=status,
            priority="normal",
            customer_id=customer_id,
            agent_id=agent_id,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket.id

    def test_list_requires_authentication(self):
        """未认证用户访问工单列表返回 401。"""
        app.dependency_overrides.clear()
        response = TestClient(app).get(self.LIST_URL)
        assert response.status_code == 401

    def test_customer_cannot_access_ticket_workbench_list(self):
        """customer 不能进入内部工单工作台列表。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=1)
        db = TestingSessionLocal()
        self._create_ticket(db, customer_id=1, title="自己的工单")
        self._create_ticket(db, customer_id=2, title="别人的工单")
        db.close()

        response = TestClient(app).get(self.LIST_URL)
        assert response.status_code == 403

    def test_list_admin_sees_all_tickets(self):
        """admin 可以看到全部工单。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=9, role="admin")
        db = TestingSessionLocal()
        self._create_ticket(db, customer_id=1, title="工单A")
        self._create_ticket(db, customer_id=2, title="工单B")
        db.close()

        response = TestClient(app).get(self.LIST_URL)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_agent_sees_open_and_own_assigned_tickets(self):
        """agent 可以看到 open 待接入工单和自己已领取的工单。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        db = TestingSessionLocal()
        self._create_ticket(db, customer_id=1, title="待接入工单", status="open")
        self._create_ticket(db, customer_id=2, title="自己的处理中工单", status="assigned", agent_id=7)
        self._create_ticket(db, customer_id=3, title="别的客服工单", status="assigned", agent_id=8)
        db.close()

        response = TestClient(app).get(self.LIST_URL)
        assert response.status_code == 200
        titles = {item["title"] for item in response.json()}
        assert titles == {"待接入工单", "自己的处理中工单"}

    def test_list_empty_returns_empty_array(self):
        """没有工单时返回空数组。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        response = TestClient(app).get(self.LIST_URL)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_detail_requires_authentication(self):
        """未认证用户访问工单详情返回 401。"""
        app.dependency_overrides.clear()
        response = TestClient(app).get(f"{self.LIST_URL}/1")
        assert response.status_code == 401

    def test_get_detail_returns_messages(self):
        """工单详情包含消息记录。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=1)
        db = TestingSessionLocal()
        ticket_id = self._create_ticket(db, customer_id=1)
        db.add(Message(
            ticket_id=ticket_id,
            sender_id=1,
            sender_role="customer",
            content="我要投诉",
            msg_type="text",
        ))
        db.commit()
        db.close()

        response = TestClient(app).get(f"{self.LIST_URL}/{ticket_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ticket_id
        assert data["title"] == "测试工单"
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "我要投诉"
        assert data["messages"][0]["sender_role"] == "customer"

    def test_get_other_users_ticket_forbidden(self):
        """customer 访问他人工单返回 403。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=1)
        db = TestingSessionLocal()
        ticket_id = self._create_ticket(db, customer_id=2)
        db.close()

        response = TestClient(app).get(f"{self.LIST_URL}/{ticket_id}")
        assert response.status_code == 403

    def test_get_admin_can_access_any_ticket(self):
        """admin 可以访问任意工单。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=9, role="admin")
        db = TestingSessionLocal()
        ticket_id = self._create_ticket(db, customer_id=2)
        db.close()

        response = TestClient(app).get(f"{self.LIST_URL}/{ticket_id}")
        assert response.status_code == 200
        assert response.json()["customer_id"] == 2

    def test_get_agent_can_access_open_ticket(self):
        """agent 可以查看 open 待接入工单。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        db = TestingSessionLocal()
        ticket_id = self._create_ticket(db, customer_id=2, status="open")
        db.close()

        response = TestClient(app).get(f"{self.LIST_URL}/{ticket_id}")
        assert response.status_code == 200

    def test_get_agent_cannot_access_other_agents_assigned_ticket(self):
        """agent 不能查看其他客服已领取的工单。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        db = TestingSessionLocal()
        ticket_id = self._create_ticket(db, customer_id=2, status="assigned", agent_id=8)
        db.close()

        response = TestClient(app).get(f"{self.LIST_URL}/{ticket_id}")
        assert response.status_code == 403

    def test_get_nonexistent_ticket_returns_404(self):
        """不存在的工单返回 404。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=1)
        response = TestClient(app).get(f"{self.LIST_URL}/9999")
        assert response.status_code == 404


class TestTicketHandling:
    """工单处理 API 测试集（领取/回复/解决/关闭）。"""

    LIST_URL = "/tickets"

    def _create_open_ticket(self, customer_id: int = 1) -> int:
        db = TestingSessionLocal()
        ticket = Ticket(
            title="处理测试",
            description="需要客服处理的工单",
            status="open",
            priority="normal",
            customer_id=customer_id,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        ticket_id = ticket.id
        db.close()
        return ticket_id

    def _set_ticket_status(self, ticket_id: int, status: str, agent_id: int | None = 7) -> None:
        db = TestingSessionLocal()
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        ticket.status = status
        ticket.agent_id = agent_id
        db.commit()
        db.close()

    def test_claim_requires_agent_role(self):
        """customer 领取工单返回 403。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=1, role="customer")
        ticket_id = self._create_open_ticket()
        response = TestClient(app).post(f"{self.LIST_URL}/{ticket_id}/claim")
        assert response.status_code == 403

    def test_claim_success(self):
        """agent 领取工单：状态变为 assigned 并记录处理人。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket()

        response = TestClient(app).post(f"{self.LIST_URL}/{ticket_id}/claim")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "assigned"
        assert data["agent_id"] == 7
        assert len(data["messages"]) == 1

    def test_admin_can_claim_ticket(self):
        """admin 也可以在客服工作台领取工单。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=9, role="admin")
        ticket_id = self._create_open_ticket()

        response = TestClient(app).post(f"{self.LIST_URL}/{ticket_id}/claim")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "assigned"
        assert data["agent_id"] == 9

    def test_claim_already_assigned_conflict(self):
        """已领取的工单再次领取返回 409。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket()
        TestClient(app).post(f"{self.LIST_URL}/{ticket_id}/claim")

        response = TestClient(app).post(f"{self.LIST_URL}/{ticket_id}/claim")
        assert response.status_code == 409

    def test_claim_nonexistent_ticket_returns_404(self):
        """领取不存在的工单返回 404。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        response = TestClient(app).post(f"{self.LIST_URL}/9999/claim")
        assert response.status_code == 404

    def test_reply_success(self):
        """agent 回复工单：追加 agent 消息。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket()

        response = TestClient(app).post(
            f"{self.LIST_URL}/{ticket_id}/reply",
            json={"content": "您好，已为您核实订单信息。"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["messages"][-1]["content"] == "您好，已为您核实订单信息。"
        assert data["messages"][-1]["sender_role"] == "agent"

    def test_reply_auto_claims_open_ticket(self):
        """回复 open 工单时自动领取（状态变为 assigned）。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket()

        response = TestClient(app).post(
            f"{self.LIST_URL}/{ticket_id}/reply",
            json={"content": "我先处理这个工单"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "assigned"
        assert data["agent_id"] == 7

    def test_reply_blank_content_returns_422(self):
        """空白回复内容返回 422。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket()
        response = TestClient(app).post(
            f"{self.LIST_URL}/{ticket_id}/reply",
            json={"content": ""},
        )
        assert response.status_code == 422

    def test_resolve_success(self):
        """agent 标记工单已解决（assigned → resolved）。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket()
        self._set_ticket_status(ticket_id, "assigned")

        response = TestClient(app).post(f"{self.LIST_URL}/{ticket_id}/resolve")
        assert response.status_code == 200
        assert response.json()["status"] == "resolved"

    def test_resolve_open_ticket_conflict(self):
        """open 状态直接标记解决返回 409。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket()

        response = TestClient(app).post(f"{self.LIST_URL}/{ticket_id}/resolve")
        assert response.status_code == 409

    def test_close_success(self):
        """agent 关闭工单（resolved → closed）。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket()
        self._set_ticket_status(ticket_id, "resolved")

        response = TestClient(app).post(f"{self.LIST_URL}/{ticket_id}/close")
        assert response.status_code == 200
        assert response.json()["status"] == "closed"

    def test_close_wrong_state_conflict(self):
        """非 resolved 状态直接关闭返回 409。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket()
        self._set_ticket_status(ticket_id, "assigned")

        response = TestClient(app).post(f"{self.LIST_URL}/{ticket_id}/close")
        assert response.status_code == 409

    def test_reply_closed_ticket_conflict(self):
        """已关闭工单回复返回 409。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket()
        self._set_ticket_status(ticket_id, "closed")

        response = TestClient(app).post(
            f"{self.LIST_URL}/{ticket_id}/reply",
            json={"content": "还想补充信息"},
        )
        assert response.status_code == 409

    def test_customer_appends_message_to_own_open_ticket(self):
        """转人工后，customer 可以继续向自己的工单追加消息。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=1, role="customer")
        ticket_id = self._create_open_ticket(customer_id=1)

        response = TestClient(app).post(
            f"{self.LIST_URL}/{ticket_id}/messages",
            json={"content": "我补充一下订单号 ORD-001"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["messages"][-1]["sender_role"] == "customer"
        assert data["messages"][-1]["content"] == "我补充一下订单号 ORD-001"

    def test_customer_cannot_append_message_to_others_ticket(self):
        """customer 不能向他人工单追加消息。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=1, role="customer")
        ticket_id = self._create_open_ticket(customer_id=2)

        response = TestClient(app).post(
            f"{self.LIST_URL}/{ticket_id}/messages",
            json={"content": "越权回复"},
        )

        assert response.status_code == 403

    def test_agent_must_use_reply_endpoint(self):
        """agent 不能走用户追加消息接口。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(user_id=7, role="agent")
        ticket_id = self._create_open_ticket(customer_id=1)

        response = TestClient(app).post(
            f"{self.LIST_URL}/{ticket_id}/messages",
            json={"content": "客服回复"},
        )

        assert response.status_code == 403
