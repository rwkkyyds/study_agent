"""阶段三知识库入库与检索测试。"""

import pytest

from app.rag.chunker import TextChunker
from app.rag.embeddings import MockEmbedding
from app.rag.retriever import Retriever
from app.rag.vector_store import InMemoryVectorStore, VectorRecord


def test_mock_embedding_is_deterministic_and_normalized():
    embedding = MockEmbedding(dimension=8)
    first = embedding.embed_query("退款规则")
    second = embedding.embed_query("退款规则")

    assert first == second
    assert len(first) == 8
    assert sum(value * value for value in first) == pytest.approx(1.0)


def test_mock_embedding_supports_batch_order():
    embedding = MockEmbedding(dimension=8)
    vectors = embedding.embed_documents(["a", "b"])

    assert len(vectors) == 2
    assert vectors[0] != vectors[1]


def test_embedding_rejects_invalid_dimension():
    with pytest.raises(ValueError):
        MockEmbedding(dimension=0)


def test_chunker_generates_overlapping_chunks():
    chunks = TextChunker(chunk_size=10, chunk_overlap=2).split_text("abcdefghij klmnop")

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert chunks[0].content == "abcdefghij"
    assert chunks[1].content.startswith("ij")


def test_chunker_handles_empty_text():
    assert TextChunker().split_text("   ") == []


def test_chunker_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        TextChunker(chunk_size=10, chunk_overlap=10)


def test_vector_store_search_returns_similarity_order():
    store = InMemoryVectorStore(dimension=2)
    store.upsert([
        VectorRecord("a", [1.0, 0.0], "A"),
        VectorRecord("b", [0.0, 1.0], "B"),
    ])

    results = store.search([1.0, 0.0], top_k=2)

    assert [record.id for record, _ in results] == ["a", "b"]
    assert results[0][1] == pytest.approx(1.0)


def test_vector_store_replaces_same_id():
    store = InMemoryVectorStore(dimension=2)
    store.upsert([VectorRecord("same", [1.0, 0.0], "old")])
    store.upsert([VectorRecord("same", [0.0, 1.0], "new")])

    assert store.count() == 1
    assert store.search([0.0, 1.0])[0][0].text == "new"


def test_vector_store_rejects_dimension_mismatch():
    store = InMemoryVectorStore(dimension=2)

    with pytest.raises(ValueError):
        store.upsert([VectorRecord("bad", [1.0], "bad")])


def test_retriever_indexes_and_searches_chunks():
    retriever = Retriever(MockEmbedding(dimension=16))
    written = retriever.index_chunks([
        ("chunk-1", "退款规则和申请流程", {"document_id": 1}),
        ("chunk-2", "配送地址修改方法", {"document_id": 2}),
    ])

    results = retriever.search("退款规则", top_k=1)

    assert written == 2
    assert len(results) == 1
    assert results[0].id == "chunk-1"
    assert results[0].metadata["document_id"] == 1


def test_retriever_rejects_blank_query():
    with pytest.raises(ValueError):
        Retriever().search("  ")


def test_retriever_empty_index_returns_empty_list():
    assert Retriever().search("知识库查询") == []
