"""
Demo 2: 简易向量库 — 用 numpy 实现向量存储与检索
学习目标：理解向量库的核心原理（存储向量 + 相似度检索）
运行方式：python demo2_simple_vectordb.py

为什么用简易实现？
  Chroma 在某些 Windows 环境下有 DLL 兼容问题。
  本 demo 用 numpy 手写向量库，展示核心原理。
  生产环境用 Milvus（第2周学）或 Chroma（Linux/Mac 无此问题）。
"""

import numpy as np
import hashlib


# ========== Embedding 函数 ==========
def text_to_vector(text: str, dim: int = 64) -> np.ndarray:
    """文本转向量（哈希模拟，真实场景用 Embedding 模型）"""
    hash_bytes = hashlib.md5(text.encode()).digest()
    vec = []
    for i in range(dim):
        seed = hashlib.md5(hash_bytes + bytes([i])).digest()
        val = int.from_bytes(seed[:4], "little") / (2**32)
        vec.append(val * 2 - 1)
    return np.array(vec)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# ========== 简易向量库 ==========
class SimpleVectorDB:
    """
    极简向量数据库，核心功能：
    1. add: 存储文本 + 向量 + 元数据
    2. query: 根据查询文本找到最相似的文档
    3. delete: 删除文档
    """

    def __init__(self):
        self.documents = []   # 文本内容
        self.vectors = []     # 向量
        self.metadatas = []   # 元数据
        self.ids = []         # 文档ID

    def add(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        """插入文档"""
        for doc, meta, doc_id in zip(documents, metadatas, ids):
            vec = text_to_vector(doc)
            self.documents.append(doc)
            self.vectors.append(vec)
            self.metadatas.append(meta)
            self.ids.append(doc_id)

    def query(self, query_text: str, n_results: int = 2, where: dict = None) -> dict: #where 是可选的过滤条件，例如 {"topic": "LLM框架"}，只在元数据中 topic=LLM框架 的文档中检索
        """向量检索：找到最相似的 n_results 个文档"""
        query_vec = text_to_vector(query_text)

        # 计算所有文档与查询的相似度
        scores = []
        for i, doc_vec in enumerate(self.vectors):
            # 元数据过滤
            if where:
                match = all(self.metadatas[i].get(k) == v for k, v in where.items())
                if not match:
                    continue
            sim = cosine_similarity(query_vec, doc_vec)
            scores.append((sim, i))

        # 按相似度降序排序
        scores.sort(reverse=True)
        top_k = scores[:n_results]

        return {
            "documents": [self.documents[i] for _, i in top_k],
            "metadatas": [self.metadatas[i] for _, i in top_k],
            "distances": [1 - sim for sim, _ in top_k],  # 距离 = 1 - 相似度
            "ids": [self.ids[i] for _, i in top_k],
        }

    def delete(self, ids: list[str]):
        """删除文档"""
        for doc_id in ids:
            if doc_id in self.ids:
                idx = self.ids.index(doc_id)
                self.documents.pop(idx)
                self.vectors.pop(idx)
                self.metadatas.pop(idx)
                self.ids.pop(idx)

    def count(self) -> int:
        return len(self.documents)


# ========== 1. 创建向量库并插入文档 ==========
print("=" * 60)
print("【1. 创建向量库并插入文档】")

db = SimpleVectorDB()

documents = [
    "FastAPI 是一个现代 Python Web 框架，基于 Starlette 和 Pydantic。",
    "LangChain 是 LLM 应用开发框架，提供 Prompt、LLM、Parser 等组件。",
    "RAG（检索增强生成）让 LLM 先检索相关文档再生成回答。",
    "Embedding 将文本转换为向量，语义相似的文本向量距离更近。",
    "Chroma 是轻量级向量数据库，适合本地开发和原型验证。",
    "Docker 容器化部署确保环境一致性，是生产部署的标准方式。",
    "Pydantic 用于数据校验，FastAPI 用它自动校验请求体。",
    "LCEL 是 LangChain 的链式表达语言，用管道符 | 串联组件。",
]

metadatas = [
    {"source": "fastapi.txt", "topic": "Web框架"},
    {"source": "langchain.txt", "topic": "LLM框架"},
    {"source": "rag.txt", "topic": "RAG"},
    {"source": "embedding.txt", "topic": "Embedding"},
    {"source": "chroma.txt", "topic": "向量数据库"},
    {"source": "docker.txt", "topic": "部署"},
    {"source": "pydantic.txt", "topic": "数据校验"},
    {"source": "lcel.txt", "topic": "LangChain"},
]

ids = [f"doc_{i}" for i in range(len(documents))]

db.add(documents, metadatas, ids)
print(f"  文档数: {db.count()}")
for i, doc in enumerate(documents):
    print(f"    [{ids[i]}] {doc[:40]}...")
print()


# ========== 2. 向量检索 ==========
print("=" * 60)
print("【2. 向量检索 — 根据问题找到最相关的文档】")

queries = [
    "FastAPI 有什么特点？",
    "什么是 RAG？",
    "如何部署服务？",
    "向量数据库有什么用？",
]

for query in queries:
    results = db.query(query, n_results=2)

    print(f"  Q: {query}")
    for doc, metadata, distance in zip(
        results["documents"],
        results["metadatas"],
        results["distances"],
    ):
        source = metadata["source"]
        print(f"    [{source}] 距离:{distance:.4f} -> {doc[:50]}...")
    print()


# ========== 3. 带过滤条件的检索 ==========
print("=" * 60)
print("【3. 带元数据过滤的检索】")

results = db.query("组件化开发", n_results=3, where={"topic": "LLM框架"})

print("  Q: 组件化开发（仅在 topic=LLM框架 中检索）")
for doc, metadata in zip(results["documents"], results["metadatas"]):
    print(f"    [{metadata['source']}] {doc[:50]}...")
print()


# ========== 4. 删除文档 ==========
print("=" * 60)
print("【4. 删除文档】")

db.delete(["doc_7"])
print(f"  删除 doc_7 后，文档数: {db.count()}")
print()


# ========== 总结 ==========
print("=" * 60)
print("【总结：向量库核心操作】")
print("""
  1. add(documents, metadatas, ids) — 存储文档
  2. query(query_text, n_results) — 向量检索
  3. query(where={...}) — 带过滤的检索
  4. delete(ids) — 删除文档

  核心原理：
    文本 -> Embedding -> 向量 -> 存入列表
    查询 -> Embedding -> 向量 -> 与所有向量计算余弦相似度 -> 返回 Top-K

  生产环境的区别：
    - 本 demo: numpy 列表，暴力搜索（O(n)）
    - Milvus/Chroma: 向量索引（HNSW/IVF），近似搜索（O(log n)），支持十亿级
""")
