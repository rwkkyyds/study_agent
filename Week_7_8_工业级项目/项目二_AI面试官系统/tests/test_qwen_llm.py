import httpx

from app.core.config import Settings
from app.schemas.interview import InterviewFollowUpRequest, InterviewQuestion, InterviewQuestionRequest
from app.services.qwen_llm import QwenInterviewLLM
from app.workflow.interview_graph import InterviewWorkflow


RESUME_TEXT = "我做过企业级智能客服 RAG 系统，使用 FastAPI、LangGraph、Milvus、Redis、PostgreSQL 和 Docker Compose。"


def test_qwen_client_parses_follow_up_json():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"follow_up_questions":["请展开缓存降级方案。","请说明上线后的核心指标。"]}'
                        }
                    }
                ]
            },
        )

    settings = Settings(
        llm_provider="qwen",
        dashscope_api_key="test-secret",
        qwen_model="qwen-plus",
        llm_max_retries=0,
    )
    llm = QwenInterviewLLM(settings=settings, transport=httpx.MockTransport(handler))

    questions = llm.generate_follow_ups(
        job_title="AI 应用开发工程师",
        question_id="q1",
        answer="我做了 RAG、Redis 缓存和 Docker 部署。",
    )

    assert questions == ["请展开缓存降级方案。", "请说明上线后的核心指标。"]
    assert captured["url"].endswith("/chat/completions")
    assert captured["authorization"] == "Bearer test-secret"


def test_workflow_uses_qwen_enrichment_when_injected():
    class FakeLLM:
        def generate_questions(self, **kwargs):
            return [
                InterviewQuestion(
                    id="qwen1",
                    question_type="qwen_deep_dive",
                    question="请结合你的 RAG 项目说明一次真实故障定位过程。",
                    expected_points=["故障现象", "定位路径", "修复结果"],
                    source="通义千问增强",
                )
            ]

        def generate_follow_ups(self, **kwargs):
            return ["请补充这次优化前后的量化指标。"]

    workflow = InterviewWorkflow(llm=FakeLLM())

    generated = workflow.generate_questions(
        InterviewQuestionRequest(
            resume_text=RESUME_TEXT,
            job_title="AI 应用开发工程师",
            difficulty="mid",
            question_count=5,
        )
    )
    follow_up = workflow.generate_follow_up(
        InterviewFollowUpRequest(
            session_id=generated.session_id,
            question_id="q1",
            answer="首先我会说明 RAG 业务、Redis 缓存、Docker 部署和监控指标。",
        ),
        job_title="AI 应用开发工程师",
    )

    assert any(question.source == "通义千问增强" for question in generated.questions)
    assert "qwen_question_enrichment_node" in generated.workflow_trace
    assert follow_up.follow_up_questions == ["请补充这次优化前后的量化指标。"]
    assert "qwen_follow_up_enrichment_node" in follow_up.workflow_trace


def test_workflow_falls_back_when_qwen_fails():
    class BrokenLLM:
        def generate_questions(self, **kwargs):
            raise RuntimeError("boom")

        def generate_follow_ups(self, **kwargs):
            raise RuntimeError("boom")

    workflow = InterviewWorkflow(llm=BrokenLLM())

    generated = workflow.generate_questions(
        InterviewQuestionRequest(
            resume_text=RESUME_TEXT,
            job_title="AI 应用开发工程师",
            difficulty="mid",
            question_count=5,
        )
    )
    follow_up = workflow.generate_follow_up(
        InterviewFollowUpRequest(
            session_id=generated.session_id,
            question_id="q1",
            answer="我做了 RAG 项目，但细节还没有展开。",
        ),
        job_title="AI 应用开发工程师",
    )

    assert len(generated.questions) == 5
    assert generated.workflow_trace[-1] == "qwen_question_enrichment_skipped"
    assert follow_up.follow_up_questions
    assert follow_up.workflow_trace[-1] == "qwen_follow_up_enrichment_skipped"
