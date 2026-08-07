"""阶段四客服 LangGraph 工作流测试。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.ticket import Ticket
from app.rag.embeddings import MockEmbedding
from app.rag.retriever import Retriever
from app.rag.vector_store import InMemoryVectorStore
from app.tools.customer_service import CustomerServiceTools

from app.workflow.customer_service import CustomerServiceWorkflow, IntentClassifier


@pytest.fixture
def workflow():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    retriever = Retriever(
        embedding=MockEmbedding(dimension=16),
        vector_store=InMemoryVectorStore(dimension=16),
    )
    retriever.index_chunks([("refund", "退款申请需要提交订单号和退款原因。", {"source": "faq"})])
    yield CustomerServiceWorkflow(CustomerServiceTools(retriever, db)), db
    db.close()


def test_intent_classifier_routes_three_intents():
    classifier = IntentClassifier()

    assert classifier.classify("退款需要什么材料") == "knowledge"
    assert classifier.classify("订单 123 的物流到哪里了") == "order"
    assert classifier.classify("请转人工客服") == "human"


def test_workflow_knowledge_route_returns_sources(workflow):
    service, _ = workflow

    result = service.run(customer_id=1, query="退款申请需要什么材料")

    assert result["intent"] == "knowledge"
    assert "退款申请" in result["answer"]
    assert result["sources"][0]["id"] == "refund"


def test_workflow_order_route_returns_order_adapter_result(workflow):
    service, _ = workflow

    result = service.run(customer_id=1, query="查询订单 123 的物流")

    assert result["intent"] == "order"
    assert result["order"]["order_id"] == "123"
    assert result["ticket_id"] is None


def test_workflow_human_route_creates_ticket_and_message(workflow):
    service, db = workflow

    result = service.run(customer_id=7, query="我想投诉，请转人工")

    assert result["intent"] == "human"
    assert result["ticket_id"] is not None
    ticket = db.query(Ticket).one()

    assert len(ticket.messages) == 1
    assert ticket.messages[0].sender_role == "system"


def test_workflow_rejects_blank_query(workflow):
    service, _ = workflow

    with pytest.raises(ValueError):
        service.run(customer_id=1, query="  ")
