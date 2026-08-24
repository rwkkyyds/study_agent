"""企业级 LLM Gateway 基础能力。

当前先承接 Qwen provider 的路由、超时、重试和 JSON 输出校验。
后续可在这里继续扩展多模型、熔断、成本统计和 Prompt 版本注册。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class LLMJsonResult:
    """LLM Gateway 标准 JSON 响应。"""

    provider: str
    model: str
    prompt_version: str
    attempts: int
    data: dict[str, Any]


class LLMGateway:
    """LLM 调用统一出口。"""

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._transport = transport

    def is_configured(self, provider: str | None = None) -> bool:
        """判断指定 provider 是否已具备调用条件。"""

        resolved_provider = (provider or self.settings.llm_provider).lower()
        if resolved_provider == "qwen":
            return bool(self.settings.dashscope_api_key)
        return False

    def chat_json(
        self,
        *,
        system_prompt: str,
        payload: dict[str, Any],
        prompt_version: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> LLMJsonResult:
        """调用指定 LLM provider，并强制解析为 JSON 对象。"""

        resolved_provider = (provider or self.settings.llm_provider).lower()
        if resolved_provider != "qwen":
            raise RuntimeError(f"LLM provider 暂不支持: {resolved_provider}")
        if not self.is_configured(resolved_provider):
            raise RuntimeError("Qwen LLM 未启用或缺少 DASHSCOPE_API_KEY")

        return self._chat_qwen_json(
            system_prompt=system_prompt,
            payload=payload,
            prompt_version=prompt_version,
            model=model or self.settings.qwen_model,
        )

    def _chat_qwen_json(
        self,
        *,
        system_prompt: str,
        payload: dict[str, Any],
        prompt_version: str,
        model: str,
    ) -> LLMJsonResult:
        request_body = {
            "model": model,
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
        max_attempts = max(1, self.settings.llm_max_retries + 1)
        for attempt in range(1, max_attempts + 1):
            try:
                with httpx.Client(
                    timeout=self.settings.llm_timeout_seconds,
                    transport=self._transport,
                    trust_env=True,
                ) as client:
                    response = client.post(url, headers=headers, json=request_body)
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                return LLMJsonResult(
                    provider="qwen",
                    model=model,
                    prompt_version=prompt_version,
                    attempts=attempt,
                    data=loads_json_object(content),
                )
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                last_error = exc

        error_name = last_error.__class__.__name__ if last_error else "UnknownError"
        raise RuntimeError(f"Qwen LLM 调用失败: {error_name}")


def llm_gateway_status(settings: Settings | None = None) -> dict[str, Any]:
    """返回 LLM Gateway 就绪摘要，供 health/ready 和部署检查使用。"""

    resolved = settings or get_settings()
    provider = resolved.llm_provider.lower()
    status = "disabled"
    model = None
    if provider == "qwen":
        status = "configured" if resolved.dashscope_api_key else "missing_api_key"
        model = resolved.qwen_model if resolved.dashscope_api_key else None
    elif provider != "mock":
        status = "unsupported_provider"

    return {
        "name": "llm_gateway",
        "status": status,
        "provider": provider,
        "model": model,
        "timeout_seconds": resolved.llm_timeout_seconds,
        "max_retries": resolved.llm_max_retries,
    }


def loads_json_object(content: str) -> dict[str, Any]:
    """从 LLM 输出中提取 JSON 对象，兼容 ```json 代码块。"""

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
        raise ValueError("LLM 返回内容不是 JSON 对象")
    return data


def clean_string_list(value: Any) -> list[str]:
    """清洗 LLM 返回的字符串数组。"""

    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
