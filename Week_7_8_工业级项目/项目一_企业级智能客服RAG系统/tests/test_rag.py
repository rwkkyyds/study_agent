"""RAG 模块单元测试：嵌入、分块、向量存储、检索。"""

from __future__ import annotations

from app.rag.chunker import TextChunker
from app.rag.embeddings import MockEmbedding
from app.rag.retriever import Retriever
from app.rag.vector_store import InMemoryVectorStore


class TestMockEmbedding:
    """MockEmbedding 测试。"""

    def test_embed_query_returns_fixed_dimension(self):
        """单个查询应返回固定维度的向量。"""

        emb = MockEmbedding(dimension=768)
        vector = emb.embed_query("hello")
        assert len(vector) == 768

    def test_embed_query_deterministic(self):
        """相同文本应返回相同向量。"""

        emb = MockEmbedding()
        v1 = emb.embed_query("same text")
        v2 = emb.embed_query("same text")
        assert v1 == v2

    def test_embed_documents_batch(self):
        """批量嵌入应返回相同数量的向量。"""

        emb = MockEmbedding()
        texts = ["a", "b", "c"]
        vectors = emb.embed_documents(texts)
        assert len(vectors) == 3
        assert all(len(v) == 768 for v in vectors)


class TestTextChunker:
    """文本分块器测试。"""

    def test_split_empty_text(self):
        """空文本应返回空列表。"""

        chunker = TextChunker()
        assert chunker.split_text("") == []

    def test_split_short_text(self):
        """短文本应返回一个块。"""

        chunker = TextChunker(chunk_size=100)
        chunks = chunker.split_text("hello world")
        assert len(chunks) == 1
        assert chunks[0]["content"] == "hello world"

    def test_split_long_text(self):
        """长文本应正确切分。"""

        chunker = TextChunker(chunk_size=10, chunk_overlap=2)
        text = "a" * 25
        chunks = chunker.split_text(text)
        assert len(chunks) >= 2
        assert all(c["content"] for c in chunks)

    def test_chunk_overlap_validation(self):
        """重叠大于块大小应抛出异常。"""

        try:
            TextChunker(chunk_size=10, chunk_overlap=20)
            assert False, "应该抛出异常"
        except ValueError:
            pass


class TestInMemoryVectorStore:
    """内存向量存储测试。"""

    def test_empty_search(self):
        """空库搜索应返回空列表。"""

        store = InMemoryVectorStore()
        results = store.similarity_search([0.0] * 768, top_k=5)
        assert results == []

    def test_add_and_search(self):
        """添加文本后应能搜索到。"""

        emb = MockEmbedding(dimension=768)
        store = InMemoryVectorStore()

        texts = ["苹果是一种水果", "香蕉是一种水果", "汽车是一种交通工具"]
        vectors = emb.embed_documents(texts)
        store.add_texts(texts, vectors)

        results = store.similarity_search(emb.embed_query("水果"), top_k=2)
        assert len(results) == 2
        assert "text" in results[0]


class TestRetriever:
    """检索器测试。"""

    def test_retrieve_empty(self):
        """空库检索应返回空列表。"""

        retriever = Retriever()
        results = retriever.retrieve("hello")
        assert results == []

    def test_retrieve_with_data(self):
        """有数据时检索应返回结果。"""

        emb = MockEmbedding(dimension=768)
        store = InMemoryVectorStore()
        retriever = Retriever(embedding=emb, vector_store=store)

        texts = ["Python 是一种编程语言", "Java 也是一种编程语言", "今天天气很好"]
        vectors = emb.embed_documents(texts)
        store.add_texts(texts, vectors)

        results = retriever.retrieve("编程语言")
        assert len(results) > 0