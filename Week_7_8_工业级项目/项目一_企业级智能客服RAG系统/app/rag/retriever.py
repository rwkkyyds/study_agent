"""检索应用服务：查询向量化、相似度搜索和结果封装。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.rag.embeddings import MockEmbedding
from app.rag.vector_store import InMemoryVectorStore, VectorRecord


@dataclass(frozen=True)
class RetrievedChunk:
    """面向上层业务的检索结果。"""

    id: str
    content: str
    score: float
    metadata: dict[str, Any]


class Retriever:
    """组合 Embedding Provider 和 Vector Store，隔离检索编排逻辑。"""

    def __init__(
        self,
        embedding: MockEmbedding | None = None,
        vector_store: InMemoryVectorStore | None = None,
    ) -> None:
        self.embedding = embedding or MockEmbedding()
        self.vector_store = vector_store or InMemoryVectorStore(self.embedding.dimension)

    def index_chunks(
        self,
        chunks: list[tuple[str, str, dict[str, Any] | None]],
    ) -> int:
        """批量写入 (id, text, metadata)，返回成功写入数量。"""

        if not chunks:
            return 0
        texts = [text for _, text, _ in chunks]
        vectors = self.embedding.embed_documents(texts)
        records = [
            VectorRecord(
                id=record_id,
                vector=vector,
                text=text,
                metadata=metadata or {},
            )
            for (record_id, text, metadata), vector in zip(chunks, vectors, strict=True)
        ]
        self.vector_store.upsert(records)
        return len(records)

    def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        """将查询嵌入后搜索，并转换为稳定的领域结果。"""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query 不能为空")
        query_vector = self.embedding.embed_query(query)
        results = self.vector_store.search(query_vector, top_k=top_k)
        return [
            RetrievedChunk(
                id=record.id,
                content=record.text,
                score=score,
                metadata=dict(record.metadata),
            )
            for record, score in results
        ]
