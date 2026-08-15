"""知识库文档管理 API 测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.documents import get_retriever
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User
from app.rag.embeddings import MockEmbedding
from app.rag.retriever import Retriever
from app.rag.vector_store import InMemoryVectorStore
from app.services.auth import get_current_user

# 使用独立的测试数据库
TEST_DATABASE_URL = "sqlite:///./test_documents.db"
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
    app.dependency_overrides.clear()


def _make_user_stub(user_id: int = 1, role: str = "customer"):
    """创建用户桩，用于覆盖 get_current_user 依赖。"""
    return type("UserStub", (), {"id": user_id, "role": role, "is_active": True})()


class TestDocuments:
    """知识库文档管理 API 测试集。"""

    UPLOAD_URL = "/documents/upload"
    LIST_URL = "/documents"
    DELETE_URL = "/documents/"

    def test_upload_requires_authentication(self):
        """未认证用户上传文档返回 401。"""
        app.dependency_overrides.clear()
        response = TestClient(app).post(self.UPLOAD_URL, params={
            "title": "test", "content": "test content"
        })
        assert response.status_code == 401

    def test_customer_upload_document_forbidden(self):
        """customer 不能录入知识库。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="customer")
        response = TestClient(app).post(self.UPLOAD_URL, params={
            "title": "退款规则",
            "content": "退款申请需要提交订单号和退款原因。",
        })
        assert response.status_code == 403

    def test_agent_upload_document_forbidden(self):
        """agent 只能查看知识库，不能录入。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="agent")
        response = TestClient(app).post(self.UPLOAD_URL, params={
            "title": "退款规则",
            "content": "退款申请需要提交订单号和退款原因。",
        })
        assert response.status_code == 403

    def test_admin_upload_success(self):
        """admin 上传文档成功，返回文档 ID、标题和切分块数。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        response = TestClient(app).post(self.UPLOAD_URL, params={
            "title": "退款规则",
            "content": "退款申请需要提交订单号和退款原因。审核通过后 3 个工作日内退款到账。",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "退款规则"
        assert data["id"] > 0
        assert data["chunks"] == 1
        assert "上传并索引成功" in data["message"]

    def test_upload_blank_title_returns_422(self):
        """空白标题返回 422。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        response = TestClient(app).post(self.UPLOAD_URL, params={
            "title": "", "content": "some content"
        })
        assert response.status_code == 422

    def test_upload_blank_content_returns_422(self):
        """空白内容返回 422。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        response = TestClient(app).post(self.UPLOAD_URL, params={
            "title": "test", "content": ""
        })
        assert response.status_code == 422

    def test_upload_long_content_produces_multiple_chunks(self):
        """长内容上传产生多个切分块。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        long_text = "测试文本。 " * 200
        response = TestClient(app).post(self.UPLOAD_URL, params={
            "title": "长文档", "content": long_text, "source": "test"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["chunks"] > 1

    def test_list_documents_requires_authentication(self):
        """未认证用户列表返回 401。"""
        app.dependency_overrides.clear()
        response = TestClient(app).get(self.LIST_URL)
        assert response.status_code == 401

    def test_customer_list_documents_forbidden(self):
        """customer 不能进入内部知识库管理页。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="customer")
        response = TestClient(app).get(self.LIST_URL)
        assert response.status_code == 403

    def test_agent_list_documents_returns_uploaded_docs(self):
        """agent 可以只读查看已录入文档。"""
        client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        client.post(self.UPLOAD_URL, params={
            "title": "文档A", "content": "内容A"
        })
        client.post(self.UPLOAD_URL, params={
            "title": "文档B", "content": "内容B"
        })
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="agent")
        response = client.get(self.LIST_URL)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "文档A"
        assert data[1]["title"] == "文档B"

    def test_admin_list_documents_returns_uploaded_docs(self):
        """admin 可以查看已录入文档。"""
        client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        upload_resp = client.post(self.UPLOAD_URL, params={
            "title": "文档A", "content": "内容A"
        })
        assert upload_resp.status_code == 201
        response = client.get(self.LIST_URL)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "文档A"

    def test_delete_document_requires_admin(self):
        """非 admin 角色删除文档返回 403。"""
        client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        upload_resp = client.post(self.UPLOAD_URL, params={
            "title": "待删除", "content": "将被删除的内容"
        })
        assert upload_resp.status_code == 201
        doc_id = upload_resp.json()["id"]
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="agent")
        response = client.delete(f"{self.DELETE_URL}{doc_id}")
        assert response.status_code == 403

    def test_delete_document_as_admin_success(self):
        """admin 角色删除文档成功返回 204。"""
        # 先以 admin 身份上传
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        client = TestClient(app)
        upload_resp = client.post(self.UPLOAD_URL, params={
            "title": "待删除", "content": "将被删除的内容"
        })
        assert upload_resp.status_code == 201
        doc_id = upload_resp.json()["id"]
        response = client.delete(f"{self.DELETE_URL}{doc_id}")
        assert response.status_code == 204

    def test_delete_document_removes_vector_index(self):
        """删除文档时同步删除对应向量索引，避免已删知识仍被检索。"""
        retriever = Retriever(
            embedding=MockEmbedding(dimension=16),
            vector_store=InMemoryVectorStore(dimension=16),
        )
        app.dependency_overrides[get_retriever] = lambda: retriever
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        client = TestClient(app)
        upload_resp = client.post(self.UPLOAD_URL, params={
            "title": "待删除索引",
            "content": "退款索引删除验证内容",
        })
        assert upload_resp.status_code == 201
        doc_id = upload_resp.json()["id"]
        assert retriever.vector_store.count() == 1

        response = client.delete(f"{self.DELETE_URL}{doc_id}")

        assert response.status_code == 204
        assert retriever.vector_store.count() == 0

    def test_delete_nonexistent_document_returns_404(self):
        """删除不存在的文档返回 404。"""
        app.dependency_overrides[get_current_user] = lambda: _make_user_stub(role="admin")
        response = TestClient(app).delete(f"{self.DELETE_URL}9999")
        assert response.status_code == 404
