"""向量存储抽象及本地内存适配器。"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VectorRecord:
    """向量记录，metadata 用于携带文档、块和来源信息。"""

    id: str
    vector: list[float]
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class InMemoryVectorStore:
    """线程内可用的本地向量库，接口设计对齐未来 Milvus 适配器。"""

    def __init__(self, dimension: int = 768) -> None:
        if dimension <= 0:
            raise ValueError("dimension 必须大于 0")
        self.dimension = dimension
        self._records: dict[str, VectorRecord] = {}

    def upsert(self, records: list[VectorRecord]) -> None:
        """新增或覆盖记录，并校验向量维度。"""

        for record in records:
            if len(record.vector) != self.dimension:
                raise ValueError(
                    f"向量维度错误：期望 {self.dimension}，实际 {len(record.vector)}"
                )
            self._records[record.id] = record

    def search(self, query_vector: list[float], top_k: int = 5) -> list[tuple[VectorRecord, float]]:
        """按余弦相似度倒序返回结果，分数范围约为 [-1, 1]。"""

        if len(query_vector) != self.dimension:
            raise ValueError(
                f"查询向量维度错误：期望 {self.dimension}，实际 {len(query_vector)}"
            )
        if top_k <= 0:
            return []

        scored = [
            (record, self._cosine_similarity(query_vector, record.vector))
            for record in self._records.values()
        ]
        scored.sort(key=lambda item: (-item[1], item[0].id))
        return scored[:top_k]

    def count(self) -> int:
        """返回当前记录数，便于健康检查和测试。"""

        return len(self._records)

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        dot_product = sum(a * b for a, b in zip(left, right, strict=True))
        return dot_product / (left_norm * right_norm)
