"""向量存储：抽象接口 + 本地内存实现。

提供统一的 VectorStore 抽象，支持：
- InMemoryVectorStore：本地开发用，不依赖外部服务
- MilvusVectorStore：生产环境用（需要 Milvus Docker）
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from app.rag.embeddings import MockEmbedding

logger = logging.getLogger(__name__)


class VectorStore:
    """向量存储抽象接口。"""

    def add_texts(
        self, texts: list[str], embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
    ) -> list[str]:
        """添加文本及其向量，返回 id 列表。"""

        raise NotImplementedError

    def similarity_search(
        self, query_vector: list[float], top_k: int = 5,
    ) -> list[dict]:
        """余弦相似度搜索，返回 [{id, text, score, metadata}, ...]。"""

        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """内存向量存储（无外部依赖）。

    所有向量保存在内存列表中，适合开发测试和小规模场景。
    生产环境请替换为 MilvusVectorStore。
    """

    def __init__(self):
        self._ids: list[str] = []
        self._texts: list[str] = []
        self._vectors: list[list[float]] = []
        self._metadatas: list[dict] = []
        self._counter = 0
        logger.info("InMemoryVectorStore initialized")

    def add_texts(
        self, texts: list[str], embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
    ) -> list[str]:
        ids = []
        for i, text in enumerate(texts):
            idx = f"mem_{self._counter}"
            self._counter += 1
            self._ids.append(idx)
            self._texts.append(text)
            self._vectors.append(embeddings[i])
            self._metadatas.append(metadatas[i] if metadatas else {})
            ids.append(idx)
        logger.info("Added %d texts to InMemoryVectorStore", len(texts))
        return ids

    def similarity_search(
        self, query_vector: list[float], top_k: int = 5,
    ) -> list[dict]:
        if not self._vectors:
            return []

        scores = []
        for i, vec in enumerate(self._vectors):
            score = self._cosine_similarity(query_vector, vec)
            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_k = min(top_k, len(scores))

        results = []
        for i in range(top_k):
            idx, score = scores[i]
            results.append({
                "id": self._ids[idx],
                "text": self._texts[idx],
                "score": round(score, 4),
                "metadata": self._metadatas[idx],
            })
        return results

    @staticmethod
    def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
        """计算余弦相似度。"""

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 * norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)