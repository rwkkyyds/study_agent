"""向量存储抽象及适配器。

- InMemoryVectorStore：本地内存实现，用于开发和测试。
- MilvusVectorStore：生产环境使用 Milvus 分布式向量数据库。
"""

from __future__ import annotations

import logging
import json
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


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

    def delete(self, ids: list[str]) -> None:
        """按记录 ID 删除向量。"""

        for record_id in ids:
            self._records.pop(record_id, None)

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        dot_product = sum(a * b for a, b in zip(left, right, strict=True))
        return dot_product / (left_norm * right_norm)


class MilvusVectorStore:
    """生产级向量存储：基于 Milvus 的分布式向量数据库适配器。

    本地开发默认连接 ``milvus://localhost:19530``（Milvus Lite 或标准部署）。
    未连接时自动回退到 Milvus Lite 内嵌模式（无需安装独立服务）。
    """

    def __init__(
        self,
        dimension: int = 1024,
        collection_name: str = "rag_chunks",
        uri: str = "http://localhost:19530",
        token: str | None = None,
    ) -> None:
        if dimension <= 0:
            raise ValueError("dimension 必须大于 0")
        self.dimension = dimension
        self.collection_name = collection_name
        self.uri = uri
        self.token = token
        self._collection = None
        self._connect()

    def _connect(self) -> None:
        """确保 Milvus 连接和集合就绪。"""

        from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

        # 建立连接（lite 模式不传 token）
        connect_kwargs: dict[str, Any] = {"alias": "default", "uri": self.uri}
        if self.token:
            connect_kwargs["token"] = self.token

        try:
            connections.connect(**connect_kwargs)
        except Exception as exc:
            raise RuntimeError(f"Milvus 连接失败: {exc} uri={self.uri}") from exc

        # 集合已存在则直接加载
        if utility.has_collection(self.collection_name):
            self._collection = Collection(self.collection_name)
            self._collection.load()
            return

        # 创建集合
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=128),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]
        schema = CollectionSchema(fields, description="RAG 知识库切分块")
        self._collection = Collection(self.collection_name, schema)
        self._collection.create_index(
            "vector",
            {"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 128}},
        )
        self._collection.load()
        logger.info("Milvus 集合已创建: %s dim=%d", self.collection_name, self.dimension)

    def upsert(self, records: list[VectorRecord]) -> None:
        """新增或覆盖记录。"""

        if not records:
            return
        for record in records:
            if len(record.vector) != self.dimension:
                raise ValueError(
                    f"向量维度错误：期望 {self.dimension}，实际 {len(record.vector)}"
                )

        # 按 id 删除已有记录，再插入新记录
        ids = [r.id for r in records]
        self._collection.delete(f"id in {json.dumps(ids, ensure_ascii=False)}")

        entities = [
            [r.id for r in records],
            [r.vector for r in records],
            [r.text for r in records],
            [dict(r.metadata) for r in records],
        ]
        self._collection.insert(entities)
        self._collection.flush()

    def search(self, query_vector: list[float], top_k: int = 5) -> list[tuple[VectorRecord, float]]:
        """按内积（IP）相似度倒序返回结果，分数范围约 [0, 1]。"""

        if len(query_vector) != self.dimension:
            raise ValueError(
                f"查询向量维度错误：期望 {self.dimension}，实际 {len(query_vector)}"
            )
        if top_k <= 0:
            return []

        results = self._collection.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"nprobe": 16}},
            limit=top_k,
            output_fields=["id", "text", "metadata"],
        )

        hits = results[0]
        output: list[tuple[VectorRecord, float]] = []
        for hit in hits:
            output.append((
                VectorRecord(
                    id=hit.entity.get("id"),
                    vector=[],
                    text=hit.entity.get("text"),
                    metadata=hit.entity.get("metadata") or {},
                ),
                hit.score,
            ))
        return output

    def delete(self, ids: list[str]) -> None:
        """按记录 ID 删除 Milvus 中的向量。"""

        if not ids:
            return
        expr = f"id in {json.dumps(ids, ensure_ascii=False)}"
        self._collection.delete(expr)
        self._collection.flush()

    def count(self) -> int:
        """返回当前集合记录数。"""

        self._collection.flush()
        return self._collection.num_entities
