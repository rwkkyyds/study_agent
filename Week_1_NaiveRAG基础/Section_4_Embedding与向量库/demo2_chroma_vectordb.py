"""
Demo 2: FAISS 向量数据库 — 真实向量索引基本操作
学习目标：掌握 FAISS 的创建、插入、查询操作，理解向量索引与暴力搜索的区别
运行方式：python demo2_chroma_vectordb.py

为什么用 FAISS？
  Chroma 1.5.x 在 Windows 上有 Rust 后端兼容问题（段错误）。
  FAISS 是 Meta 开源的向量检索库，纯 C++ 后端，Windows 兼容性好。
  生产环境也可以用 Milvus（第2周学）。
"""

import numpy as np
import faiss
import hashlib


# ========== Embedding 函数 ==========
def text_to_vector(text: str, dim: int = 64) -> np.ndarray:
    """文本转向量（哈希模拟，真实场景用 OpenAI/Sentence-Transformers）"""
    hash_bytes = hashlib.md5(text.encode()).digest()
    vec = []
    for i in range(dim):
        seed = hashlib.md5(hash_bytes + bytes([i])).digest()
        val = int.from_bytes(seed[:4], "little") / (2**32)
        vec.append(val * 2 - 1)
    return np.array(vec, dtype=np.float32)


# ========== 1. 创建 FAISS 索引 ==========
print("=" * 60)
print("【1. 创建 FAISS 向量索引】")

dim = 64  # 向量维度
index = faiss.IndexFlatIP(dim)  # index是一个 FAISS 索引对象，IndexFlatIP 表示使用内积作为相似度度量，适合小规模数据的暴力搜索

# 文档存储（FAISS 只存向量，文本和元数据需要自己管理）
doc_store = []       # 文本内容
metadata_store = []  # 元数据
id_store = []        # 文档ID

print(f"  索引类型: IndexFlatIP（内积，暴力搜索）")
print(f"  向量维度: {dim}")
print(f"  当前文档数: {index.ntotal}")
print()


# ========== 2. 插入文档 ==========
print("=" * 60)
print("【2. 插入文档（文本 + 元数据 + 向量）】")

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

# 文本 -> 向量 -> 存入 FAISS 索引
vectors = np.array([text_to_vector(doc) for doc in documents], dtype=np.float32)
faiss.normalize_L2(vectors)  # 归一化，这样内积 = 余弦相似度
index.add(vectors)

# 同步存储文本和元数据
doc_store.extend(documents)
metadata_store.extend(metadatas)
id_store.extend(ids)

print(f"  插入文档数: {index.ntotal}")
for i, doc in enumerate(documents):
    print(f"    [{ids[i]}] {doc[:40]}...")
print()


# ========== 3. 向量检索（核心操作） ==========
print("=" * 60)
print("【3. 向量检索 — 根据问题找到最相关的文档】")

queries = [
    "FastAPI 有什么特点？",
    "什么是 RAG？",
    "如何部署服务？",
    "向量数据库有什么用？",
]

for query in queries:
    query_vec = text_to_vector(query).reshape(1, -1).astype(np.float32) #文本转向量，reshape成 (1, dim)，FAISS 要求查询向量是二维的
    faiss.normalize_L2(query_vec) #归一化查询向量，保持与索引中向量的相似度计算一致

    # search 返回 (相似度数组, 索引数组)
    scores, indices = index.search(query_vec, k=2) #检索最相似的2个文档，scores 是相似度分数，indices 是对应的文档索引

    print(f"  Q: {query}")
    for score, idx in zip(scores[0], indices[0]):
        source = metadata_store[idx]["source"]
        print(f"    [{source}] 相似度:{score:.4f} -> {doc_store[idx][:50]}...")
    print()


# ========== 4. 带过滤条件的检索 ==========
print("=" * 60)
print("【4. 带元数据过滤的检索】")

query = "组件化开发"
query_vec = text_to_vector(query).reshape(1, -1).astype(np.float32)
faiss.normalize_L2(query_vec)

# FAISS 没有内置元数据过滤，需要手动实现
# 先检索更多结果，再过滤
scores, indices = index.search(query_vec, k=index.ntotal)

print(f"  Q: {query}（仅在 topic=LLM框架 中检索）")
count = 0
for score, idx in zip(scores[0], indices[0]):
    if metadata_store[idx]["topic"] == "LLM框架":
        print(f"    [{metadata_store[idx]['source']}] 相似度:{score:.4f} -> {doc_store[idx][:50]}...")
        count += 1
        if count >= 3:
            break
print()


# ========== 5. 持久化保存与加载 ==========
print("=" * 60)
print("【5. 索引持久化（保存到磁盘 + 重新加载）】")

import os

save_dir = "./faiss_data"
os.makedirs(save_dir, exist_ok=True)

# 保存索引
faiss.write_index(index, os.path.join(save_dir, "knowledge.index"))

# 保存元数据（FAISS 不管文本，需要单独存）
import json
meta_path = os.path.join(save_dir, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump({"documents": doc_store, "metadatas": metadata_store, "ids": id_store}, f, ensure_ascii=False)

print(f"  索引已保存: {save_dir}/knowledge.index")
print(f"  元数据已保存: {save_dir}/metadata.json")

# 重新加载
loaded_index = faiss.read_index(os.path.join(save_dir, "knowledge.index"))
with open(meta_path, "r", encoding="utf-8") as f:
    loaded_meta = json.load(f)

print(f"  重新加载后文档数: {loaded_index.ntotal}")

# 验证加载后能正常检索
query_vec = text_to_vector("RAG 原理").reshape(1, -1).astype(np.float32)
faiss.normalize_L2(query_vec)
scores, indices = loaded_index.search(query_vec, k=1)
print(f"  验证检索: Q='RAG 原理' -> [{loaded_meta['metadatas'][indices[0][0]]['source']}] {loaded_meta['documents'][indices[0][0]][:40]}...")
#indices[0][0] 是最相似文档的索引，loaded_meta['documents'][...] 是对应的文本内容，loaded_meta['metadatas'][...] 是对应的元数据
print()

# 清理
import shutil
shutil.rmtree(save_dir, ignore_errors=True)


# ========== 总结 ==========
print("=" * 60)
print("【总结：FAISS 向量索引操作】")
print("""
  1. 创建索引: faiss.IndexFlatIP(dim) — 内积索引（暴力搜索）
  2. 归一化:   faiss.normalize_L2(vectors) — 让内积 = 余弦相似度
  3. 插入向量: index.add(vectors) — FAISS 只管向量，文本自己存
  4. 向量检索: index.search(query_vec, k) — 返回 (相似度, 索引)
  5. 持久化:   faiss.write_index() / faiss.read_index()

  数据流：文本 -> Embedding -> 归一化 -> 存入FAISS索引
          查询 -> Embedding -> 归一化 -> search返回Top-K索引 -> 用索引取文本

  FAISS vs 简易向量库(demo2_simple) 的区别：
    - 简易版: Python列表 + 暴力遍历 O(n)，适合理解原理
    - FAISS:  C++底层 + 向量索引，支持 IVF/HNSW 等近似搜索 O(log n)
    - 本demo用 IndexFlatIP（暴力），生产用 IndexIVFFlat 或 IndexHNSWFlat
""")
