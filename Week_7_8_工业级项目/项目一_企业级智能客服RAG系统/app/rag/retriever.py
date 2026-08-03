"""检索器：将用户查询转为向量 → 相似度搜索 → 返回结果。

支持简单的 RAG 检索流程，后续可扩展为混合检索 + Rerank。
"""

from __future__ import annotations

import logging
from typing import Optional

from app.rag.embeddings import MockEmbedding
from app.rag.vector_store import InMemoryVectorStore, VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """检索器：Embedding + VectorStore 的组合。

    职责：
    1. 将用户查询转为向量
    2. 在向量库中搜索相似块
    3. 返回排序后的文本块列表
    """

    def __init__(
        self,
        embedding: Optional[MockEmbedding] = None,
        vector_store: Optional[VectorStore] = None,
        top_k: int = 5,
    ):
        self.embedding = embedding or MockEmbedding()
        self.vector_store = vector_store or InMemoryVectorStore()
        self.top_k = top_k
        logger.info("Retriever initialized: top_k=%d", top_k)

    def retrieve(self, query: str) -> list[dict]:
        """检索与查询最相关的文本块。"""

        query_vector = self.embedding.embed_query(query)
        results = self.vector_store.similarity_search(query_vector, top_k=self.top_k)
        logger.info("Retrieved %d results for query", len(results))
        return results