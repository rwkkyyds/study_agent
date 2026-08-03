"""RAG 模块：企业知识库文档检索核心。"""

from app.rag.embeddings import MockEmbedding
from app.rag.vector_store import InMemoryVectorStore

__all__ = ["MockEmbedding", "InMemoryVectorStore"]