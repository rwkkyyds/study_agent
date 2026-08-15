"""检索应用服务：查询向量化、相似度搜索和结果封装。"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.core.config import Settings, get_settings
from app.rag.embeddings import DashScopeEmbedding, MockEmbedding
from app.rag.vector_store import InMemoryVectorStore, MilvusVectorStore, VectorRecord


@dataclass(frozen=True)
class RetrievedChunk:
    """面向上层业务的检索结果。"""

    id: str
    content: str
    score: float
    metadata: dict[str, Any]


def _default_embedding(settings: Settings | None = None) -> MockEmbedding | DashScopeEmbedding:
    """根据配置决定默认 Embedding 实现。"""

    settings = settings or get_settings()
    if settings.dashscope_api_key:
        return DashScopeEmbedding(dashscope_api_key=settings.dashscope_api_key)
    return MockEmbedding()


def _default_vector_store(
    settings: Settings,
    embedding: MockEmbedding | DashScopeEmbedding,
) -> InMemoryVectorStore | MilvusVectorStore:
    """根据配置选择内存向量库或 Milvus。"""

    if settings.vector_store_type == "milvus":
        return MilvusVectorStore(
            dimension=embedding.dimension,
            collection_name=settings.milvus_collection_name,
            uri=settings.milvus_uri or "http://localhost:19530",
            token=settings.milvus_token,
        )
    return InMemoryVectorStore(embedding.dimension)


class Retriever:
    """组合 Embedding Provider 和 Vector Store，隔离检索编排逻辑。

    开发测试使用 MockEmbedding + InMemoryVectorStore，
    生产环境可传入 DashScopeEmbedding + MilvusVectorStore。
    """

    def __init__(
        self,
        embedding: MockEmbedding | DashScopeEmbedding | None = None,
        vector_store: InMemoryVectorStore | MilvusVectorStore | None = None,
    ) -> None:
        self.embedding = embedding if embedding is not None else _default_embedding()
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

    def delete_chunks(self, ids: list[str]) -> None:
        """从向量库删除指定 chunk ID。"""

        if not ids:
            return
        self.vector_store.delete(ids)

    def format_context(self, chunks: list[RetrievedChunk]) -> str:
        """将检索结果拼接为 LLM 可用的上下文文本。"""

        parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("title", f"来源 {i}")
            parts.append(f"[{source}]\n{chunk.content}")
        return "\n\n---\n\n".join(parts)


@lru_cache(maxsize=1)
def get_shared_retriever() -> Retriever:
    """返回当前进程共享的检索器，保证上传和聊天使用同一份索引。"""

    settings = get_settings()
    embedding = _default_embedding(settings)
    vector_store = _default_vector_store(settings, embedding)
    return Retriever(embedding=embedding, vector_store=vector_store)
