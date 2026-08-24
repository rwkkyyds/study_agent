"""通义千问面试增强客户端。"""

from __future__ import annotations

import httpx
from typing import Any

from app.core.config import Settings, get_settings
from app.schemas.interview import InterviewQuestion
from app.services.llm_gateway import LLMGateway, clean_string_list

QUESTION_PROMPT_VERSION = "interview.questions.qwen.v1"
FOLLOW_UP_PROMPT_VERSION = "interview.follow_up.qwen.v1"


QUESTION_SYSTEM_PROMPT = """
你是企业级 AI 面试官。请基于输入生成更贴近候选人经历的技术追问题。
只输出 JSON 对象，格式为：
{"questions":[{"question_type":"qwen_deep_dive","question":"问题","expected_points":["要点1","要点2"]}]}
""".strip()

FOLLOW_UP_SYSTEM_PROMPT = """
你是企业级 AI 面试官。请先判断候选人的回答是否回应了原题，再生成 0-2 个递进追问。
如果回答明显答非所问，只生成 1 个把候选人拉回原题的追问。
如果回答完整且有证据，只生成 1 个更深入的追问，不要为了凑数生成问题。
只输出 JSON 对象，格式为：
{"follow_up_questions":["追问1","追问2"]}
""".strip()


class QwenInterviewLLM:
    """通过 DashScope OpenAI 兼容接口调用 Qwen。"""

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
        gateway: LLMGateway | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.gateway = gateway or LLMGateway(settings=self.settings, transport=transport)

    @property
    def configured(self) -> bool:
        return self.settings.llm_provider == "qwen" and self.gateway.is_configured("qwen")

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
            points = clean_string_list(item.get("expected_points", []))[:5]
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

    def generate_follow_ups(
        self,
        *,
        job_title: str,
        question_id: str,
        answer: str,
        question: str = "",
    ) -> list[str]:
        payload = {
            "job_title": job_title,
            "question_id": question_id,
            "question": question[:1000],
            "answer": answer[:2500],
        }
        data = self._chat_json(FOLLOW_UP_SYSTEM_PROMPT, payload)
        return clean_string_list(data.get("follow_up_questions", []))[:2]

    def _chat_json(self, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        prompt_version = (
            QUESTION_PROMPT_VERSION
            if system_prompt == QUESTION_SYSTEM_PROMPT
            else FOLLOW_UP_PROMPT_VERSION
        )
        return self.gateway.chat_json(
            system_prompt=system_prompt,
            payload=payload,
            prompt_version=prompt_version,
            provider="qwen",
        ).data


def build_interview_llm(settings: Settings | None = None) -> QwenInterviewLLM | None:
    resolved = settings or get_settings()
    if resolved.llm_provider != "qwen":
        return None
    return QwenInterviewLLM(resolved)
