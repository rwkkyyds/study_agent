"""通义千问面试增强客户端。"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.schemas.interview import InterviewQuestion


QUESTION_SYSTEM_PROMPT = """
你是企业级 AI 面试官。请基于输入生成更贴近候选人经历的技术追问题。
只输出 JSON 对象，格式为：
{"questions":[{"question_type":"qwen_deep_dive","question":"问题","expected_points":["要点1","要点2"]}]}
""".strip()

FOLLOW_UP_SYSTEM_PROMPT = """
你是企业级 AI 面试官。请基于候选人回答生成最多 3 个递进追问。
只输出 JSON 对象，格式为：
{"follow_up_questions":["追问1","追问2","追问3"]}
""".strip()


class QwenInterviewLLM:
    """通过 DashScope OpenAI 兼容接口调用 Qwen。"""

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._transport = transport

    @property
    def configured(self) -> bool:
        return self.settings.llm_provider == "qwen" and bool(self.settings.dashscope_api_key)

    def generate_questions(
        self,
        *,
        resume_text: str,
        job_title: str,
        difficulty: str,
        question_count: int,
        current_questions: list[InterviewQuestion],
    ) -> list[InterviewQuestion]:
        payload = {
            "job_title": job_title,
            "difficulty": difficulty,
            "question_count": min(2, question_count),
            "resume_text": resume_text[:2500],
            "current_questions": [item.model_dump() for item in current_questions[:4]],
        }
        data = self._chat_json(QUESTION_SYSTEM_PROMPT, payload)
        questions: list[InterviewQuestion] = []
        for index, item in enumerate(data.get("questions", []), start=1):
            question = str(item.get("question", "")).strip()
            points = _clean_string_list(item.get("expected_points", []))[:5]
            if not question or not points:
                continue
            questions.append(
                InterviewQuestion(
                    id=f"qwen{index}",
                    question_type=str(item.get("question_type") or "qwen_deep_dive")[:40],
                    question=question,
                    expected_points=points,
                    source="通义千问增强",
                )
            )
        return questions[:2]

    def generate_follow_ups(self, *, job_title: str, question_id: str, answer: str) -> list[str]:
        payload = {
            "job_title": job_title,
            "question_id": question_id,
            "answer": answer[:2500],
        }
        data = self._chat_json(FOLLOW_UP_SYSTEM_PROMPT, payload)
        return _clean_string_list(data.get("follow_up_questions", []))[:3]

    def _chat_json(self, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("Qwen LLM 未启用或缺少 DASHSCOPE_API_KEY")

        request_body = {
            "model": self.settings.qwen_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0.2,
        }
        url = f"{self.settings.dashscope_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for _ in range(max(1, self.settings.llm_max_retries + 1)):
            try:
                with httpx.Client(timeout=self.settings.llm_timeout_seconds, transport=self._transport) as client:
                    response = client.post(url, headers=headers, json=request_body)
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                return _loads_json_object(content)
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                last_error = exc

        error_name = last_error.__class__.__name__ if last_error else "UnknownError"
        raise RuntimeError(f"Qwen LLM 调用失败: {error_name}")


def build_interview_llm(settings: Settings | None = None) -> QwenInterviewLLM | None:
    resolved = settings or get_settings()
    if resolved.llm_provider != "qwen":
        return None
    return QwenInterviewLLM(resolved)


def _loads_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))

    if not isinstance(data, dict):
        raise ValueError("Qwen LLM 返回内容不是 JSON 对象")
    return data


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
