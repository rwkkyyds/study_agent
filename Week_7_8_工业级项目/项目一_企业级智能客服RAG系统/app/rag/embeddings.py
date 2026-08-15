"""Embedding 实现。

- MockEmbedding：本地确定性实现，用于开发和自动化测试。
- DashScopeEmbedding：生产环境使用通义千问 text-embedding-v3 的远程调用。
"""

from __future__ import annotations

import hashlib
import logging
import math
from collections.abc import Sequence
from typing import Any

logger = logging.getLogger(__name__)


class MockEmbedding:
    """将文本稳定映射为固定维度的归一化向量。"""

    def __init__(self, dimension: int = 768) -> None:
        if dimension <= 0:
            raise ValueError("dimension 必须大于 0")
        self.dimension = dimension

    def embed_query(self, text: str) -> list[float]:
        """生成单条查询向量。"""

        return self._embed(text)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """批量生成文档向量，保持输入顺序。"""

        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise TypeError("text 必须是字符串")

        values: list[float] = []
        counter = 0
        while len(values) < self.dimension:
            digest = hashlib.sha256(f"{text}\x00{counter}".encode("utf-8")).digest()
            values.extend((byte / 127.5) - 1.0 for byte in digest)
            counter += 1

        vector = values[: self.dimension]
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return [0.0] * self.dimension
        return [value / norm for value in vector]


class DashScopeEmbedding:
    """生产级 Embedding：通过 DashScope API 调用通义千问 text-embedding-v3。

    接口与 MockEmbedding 一致，可在 Retriever 中互换使用。
    ``dashscope_api_key`` 可传入；为 None 时自动从环境变量 DASHSCOPE_API_KEY 读取。
    """

    def __init__(
        self,
        dimension: int = 1024,
        model: str = "text-embedding-v3",
        dashscope_api_key: str | None = None,
        batch_size: int = 10,
    ) -> None:
        if dimension <= 0:
            raise ValueError("dimension 必须大于 0")
        if batch_size <= 0 or batch_size > 10:
            raise ValueError("DashScope Embedding batch_size 必须在 1 到 10 之间")
        self.dimension = dimension
        self.model = model
        self._api_key = dashscope_api_key
        self.batch_size = batch_size

    def embed_query(self, text: str) -> list[float]:
        """生成单条查询向量。"""

        result = self._call_api([text])
        return result[0] if result else []

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """批量生成文档向量，按 DashScope 单批最多 10 条限制自动分批。"""

        all_texts = list(texts)
        vectors: list[list[float]] = []
        for start in range(0, len(all_texts), self.batch_size):
            batch = all_texts[start : start + self.batch_size]
            vectors.extend(self._call_api(batch))
        return vectors

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """调用 DashScope TextEmbedding API 并返回向量列表。"""

        if not texts:
            return []
        if len(texts) > 10:
            raise ValueError("DashScope Embedding 单批输入不能超过 10 条")

        import dashscope

        kwargs: dict[str, Any] = {
            "model": self.model,
            "input": texts,
            "dimension": self.dimension,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key

        resp = dashscope.TextEmbedding.call(**kwargs)
        if resp.status_code != 200:
            raise RuntimeError(
                f"DashScope Embedding API 调用失败: status={resp.status_code} message={resp.message}"
            )

        # 按输入顺序整理向量
        outputs: list[list[float]] = [None] * len(texts)  # type: ignore[list-item]
        for item in resp.output.get("embeddings", []):
            idx = item.get("text_index")
            if idx is not None and 0 <= idx < len(outputs):
                outputs[idx] = item["embedding"]

        if any(v is None for v in outputs):
            raise RuntimeError(
                f"DashScope Embedding 返回不完整：期望 {len(texts)} 条，实际返回 {sum(1 for v in outputs if v is not None)} 条"
            )

        return outputs  # type: ignore[return-value]
