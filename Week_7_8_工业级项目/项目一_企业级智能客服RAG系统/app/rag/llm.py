"""LLM 回答生成服务。

通过 DashScope API 调用通义千问（Qwen）模型，实现知识库检索后的回答生成。
支持角色设定、流式接口预留，后续可接入 LangChain 统一调用链。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 系统提示词：客服 RAG 助手的角色定义
SYSTEM_PROMPT = """你是一个专业的企业智能客服助手，名为「小R」。请遵循以下规则回答用户问题：
1. 如果提供了知识库上下文，请严格基于上下文回答，不要编造信息，并在末尾注明参考来源。
2. 如果没有提供知识库上下文，可以基于你的知识友好地回答问候、闲聊等一般性问题。
3. 如果用户问题超出你的能力范围，请如实告知并建议联系人工客服。
4. 使用友好的中文回答，语气专业、简洁、亲切。
5. 如果用户询问订单状态，引导用户提供订单号以便查询。"""


class QwenLLM:
    """通过 DashScope API 调用通义千问模型。

    ``dashscope_api_key`` 可传入；为 None 时自动从配置读取 DASHSCOPE_API_KEY。
    """

    def __init__(
        self,
        model: str = "qwen-plus",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        dashscope_api_key: str | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._api_key = dashscope_api_key or get_settings().dashscope_api_key

    def generate(
        self,
        query: str,
        context: str = "",
        history: list[dict[str, str]] | None = None,
        model: str | None = None,
    ) -> str:
        """生成回答。

        Args:
            query: 用户当前问题。
            context: 知识库检索结果拼接的上下文文本。
            history: 可选的对话历史（[{"role": "user"/"assistant", "content": "..."}]）。
            model: 临时覆盖初始化的模型名称（如 qwen-max），不传则使用默认模型。

        Returns:
            生成的回答文本。
        """

        messages = self._build_messages(query, context, history or [])
        return self._call_api(messages, model=model)

    def stream_generate(
        self,
        query: str,
        context: str = "",
        history: list[dict[str, str]] | None = None,
        model: str | None = None,
    ):
        """流式生成回答，逐块返回模型增量文本。"""

        messages = self._build_messages(query, context, history or [])
        yield from self._call_api_stream(messages, model=model)

    def _build_messages(
        self,
        query: str,
        context: str,
        history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """构建完整的消息列表（系统提示 + 历史 + 当前上下文 + 用户问题）。"""

        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 对话历史
        for msg in history:
            messages.append(msg)

        # 知识库上下文 + 用户问题
        if context:
            context_block = f"知识库上下文：\n{context}\n\n请基于以上上下文回答用户问题。"
            messages.append({"role": "user", "content": f"{context_block}\n\n用户问题：{query}"})
        else:
            messages.append({"role": "user", "content": query})

        return messages

    def _call_api(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        """调用 DashScope Generation API 并返回回答文本。

        Args:
            messages: 消息列表。
            model: 临时模型名称覆盖；不传则使用 self.model。
        """

        import dashscope

        current_model = model or self.model
        kwargs: dict[str, Any] = {
            "model": current_model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "result_format": "message",
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key

        resp = dashscope.Generation.call(**kwargs)
        if resp.status_code != 200:
            raise RuntimeError(
                f"DashScope LLM API 调用失败: status={resp.status_code} message={resp.message}"
            )

        return resp.output.choices[0].message.content  # type: ignore[union-attr, return-value]

    def _call_api_stream(self, messages: list[dict[str, str]], model: str | None = None):
        """调用 DashScope Generation 流式 API，返回增量文本。"""

        import dashscope

        current_model = model or self.model
        kwargs: dict[str, Any] = {
            "model": current_model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "result_format": "message",
            "stream": True,
            "incremental_output": True,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key

        for resp in dashscope.Generation.call(**kwargs):
            if resp.status_code != 200:
                raise RuntimeError(
                    f"DashScope LLM API 流式调用失败: status={resp.status_code} message={resp.message}"
                )
            content = resp.output.choices[0].message.content  # type: ignore[union-attr]
            if content:
                yield content

    def count_tokens(self, text: str) -> int:
        """估算文本 token 数（中文约 1.5 字/token，英文约 4 字/token）。"""

        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars / 4) + 1
