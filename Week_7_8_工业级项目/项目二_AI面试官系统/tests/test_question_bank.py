from app.services.question_bank import QuestionBankRetriever
from app.schemas.question_bank import QuestionBankSearchRequest


def test_question_bank_search_requires_auth(client):
    response = client.post("/question-bank/search", json={
        "job_title": "AI 应用开发工程师",
        "resume_text": "RAG FastAPI Milvus Docker",
        "difficulty": "mid",
    })

    assert response.status_code == 403 or response.status_code == 401


def test_question_bank_search_returns_ranked_items(client, auth_headers):
    response = client.post("/question-bank/search", json={
        "job_title": "AI 应用开发工程师",
        "resume_text": "我做过 RAG 知识库，使用 FastAPI、Milvus、Redis 和 Docker。",
        "difficulty": "mid",
        "top_k": 3,
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "RAG" in data["query_keywords"]
    assert data["items"]
    assert data["items"][0]["score"] >= data["items"][-1]["score"]
    assert any(item["question_type"] == "rag" for item in data["items"])


def test_question_bank_retriever_converts_items_to_interview_questions():
    retriever = QuestionBankRetriever()
    questions = retriever.retrieve_for_interview(
        job_title="AI 应用开发工程师",
        resume_text="RAG Milvus LangGraph Docker",
        difficulty="mid",
        top_k=2,
    )

    assert len(questions) == 2
    assert questions[0].id == "kb1"
    assert "岗位题库" in questions[0].source


def test_interview_questions_mix_resume_and_question_bank(client, auth_headers):
    response = client.post("/interviews/questions", json={
        "resume_text": "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。",
        "job_title": "AI 应用开发工程师",
        "difficulty": "mid",
        "question_count": 6,
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "rag_retrieval_node" in data["workflow_trace"]
    assert any(question["id"].startswith("kb") for question in data["questions"])
    assert any("岗位题库" in question["source"] for question in data["questions"])
