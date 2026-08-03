"""嵌入模型：本地 Mock 实现，无需外部 API Key。

生产环境可替换为 fastembed、OpenAI、或其他 Embedding 服务。
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MockEmbedding:
    """本地 Mock 嵌入模型。

    使用文本的 SHA-256 哈希生成固定维度向量（768 维），
    保证相同文本产生相同向量，不同文本向量不同。

    适用于：
    - 本地开发和无 API Key 环境
    - 功能测试和链路验证
    - CI/CD 管道

    生产环境替换为：
    - fastembed.FastEmbedEmbeddings（本地 BGE 模型）
    - OpenAIEmbeddings（需要 API Key）
    - SentenceTransformerEmbeddings（本地 SBERT 模型）
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        logger.info("MockEmbedding initialized, dimension=%d", dimension)

    def embed_query(self, text: str) -> list[float]:
        """将单个文本转为向量。"""

        return self._hash_to_vector(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转为向量。"""

        return [self._hash_to_vector(t) for t in texts]

    def _hash_to_vector(self, text: str) -> list[float]:
        """用 SHA-256 哈希生成固定维度向量。

        将哈希字节映射到 [-1, 1] 范围，保证语义无关但格式兼容。
        """

        digest = hashlib.sha256(text.encode()).digest()
        vector = []
        for i in range(self.dimension):
            byte_val = digest[i % 32]  # 32 bytes in SHA-256
            normalized = (byte_val / 127.5) - 1.0  # 映射到 [-1, 1]
            vector.append(normalized)
        return vector