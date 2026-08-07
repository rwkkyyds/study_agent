"""本地 Mock Embedding 实现。

该实现用于开发和自动化测试，保证项目在没有外部 API Key 时仍能运行。
生产环境可通过相同接口替换为真实 Embedding Provider。
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence


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
