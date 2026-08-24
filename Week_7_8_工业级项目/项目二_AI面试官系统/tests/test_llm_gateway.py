import httpx

from app.core.config import Settings
from app.services.llm_gateway import LLMGateway, llm_gateway_status, loads_json_object


def test_llm_gateway_routes_qwen_and_validates_json():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '```json\n{"ok": true, "items": ["a"]}\n```'}}]},
        )

    settings = Settings(
        llm_provider="qwen",
        dashscope_api_key="test-secret",
        qwen_model="qwen-plus",
        llm_max_retries=0,
    )
    gateway = LLMGateway(settings=settings, transport=httpx.MockTransport(handler))

    result = gateway.chat_json(
        system_prompt="只输出 JSON",
        payload={"input": "hello"},
        prompt_version="test.prompt.v1",
    )

    assert result.provider == "qwen"
    assert result.model == "qwen-plus"
    assert result.prompt_version == "test.prompt.v1"
    assert result.attempts == 1
    assert result.data == {"ok": True, "items": ["a"]}
    assert captured["url"].endswith("/chat/completions")
    assert captured["authorization"] == "Bearer test-secret"


def test_llm_gateway_status_reports_missing_qwen_key():
    status = llm_gateway_status(Settings(llm_provider="qwen", dashscope_api_key=None))

    assert status["name"] == "llm_gateway"
    assert status["status"] == "missing_api_key"
    assert status["provider"] == "qwen"
    assert status["model"] is None


def test_loads_json_object_rejects_non_object():
    try:
        loads_json_object("[1, 2, 3]")
    except ValueError as exc:
        assert "JSON 对象" in str(exc)
    else:
        raise AssertionError("列表不应被接受为 LLM Gateway JSON 对象")
