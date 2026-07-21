"""
Demo 3: 完整的 RAG 检索链路 — 分块 + 向量化 + 检索
学习目标：把文档分块和向量检索串联成完整的 RAG 数据流
运行方式：python demo3_rag_retrieval.py
"""

import numpy as np
import hashlib


# ========== 工具函数 ==========
def text_to_vector(text: str, dim: int = 64) -> np.ndarray:
    hash_bytes = hashlib.md5(text.encode()).digest()
    vec = []
    for i in range(dim):
        seed = hashlib.md5(hash_bytes + bytes([i])).digest()
        val = int.from_bytes(seed[:4], "little") / (2**32)
        vec.append(val * 2 - 1)
    return np.array(vec)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# ========== 简易分块器 ==========
def simple_splitter(text: str, chunk_size: int = 200, overlap: int = 40) -> list[str]:
    """简易递归分块器（不依赖 langchain_text_splitters）"""
    separators = ["\n\n", "\n", "。", "，", " "]
    chunks = []

    def split_recursive(text, sep_idx=0):
        if len(text) <= chunk_size:
            chunks.append(text.strip())
            return
        if sep_idx >= len(separators):
            # 所有分隔符都试过了，按字符强制切
            for i in range(0, len(text), chunk_size - overlap):
                chunks.append(text[i:i + chunk_size].strip())
            return

        sep = separators[sep_idx]
        parts = text.split(sep)

        current = ""
        for part in parts:
            if len(current) + len(part) + len(sep) <= chunk_size:
                current += (sep if current else "") + part
            else:
                if current:
                    chunks.append(current.strip())
                current = part

        if current:
            if len(current) > chunk_size:
                split_recursive(current, sep_idx + 1)
            else:
                chunks.append(current.strip())

    split_recursive(text)

    # 添加 overlap
    if overlap > 0 and len(chunks) > 1: # 只有在有多个块时才添加重叠
        overlapped = [chunks[0]] # 第一个块不重叠
        for i in range(1, len(chunks)): # 从第二个块开始添加重叠
            prev_tail = chunks[i - 1][-overlap:] # 上一个块的结尾部分
            overlapped.append(prev_tail + chunks[i]) # 当前块加上上一个块的结尾部分
        return overlapped
    return chunks


# ========== 简易向量库 ==========
class SimpleVectorDB:
    def __init__(self):
        self.documents = []
        self.vectors = []
        self.metadatas = []
        self.ids = []

    def add(self, documents, metadatas, ids):
        for doc, meta, doc_id in zip(documents, metadatas, ids):
            self.documents.append(doc)
            self.vectors.append(text_to_vector(doc))
            self.metadatas.append(meta)
            self.ids.append(doc_id)

    def query(self, query_text, n_results=2):
        query_vec = text_to_vector(query_text)
        scores = []
        for i, doc_vec in enumerate(self.vectors):
            sim = cosine_similarity(query_vec, doc_vec)
            scores.append((sim, i))
        scores.sort(reverse=True)
        top_k = scores[:n_results]
        return {
            "documents": [self.documents[i] for _, i in top_k],
            "metadatas": [self.metadatas[i] for _, i in top_k],
            "distances": [1 - sim for sim, _ in top_k],
        }

    def count(self):
        return len(self.documents)


# ========== 知识库文档 ==========
knowledge_docs = {
    "fastapi.txt": """FastAPI 入门指南

FastAPI 是一个现代 Python Web 框架，基于 Starlette 和 Pydantic。
主要特点：高性能、自动文档、类型安全。
安装方式：pip install fastapi uvicorn
运行命令：uvicorn main:app --reload

路由定义使用装饰器：
@app.get("/") 定义GET请求
@app.post("/items") 定义POST请求
路径参数用 {} 包裹：@app.get("/items/{item_id}")""",

    "langchain.txt": """LangChain 核心组件

LangChain 是 LLM 应用开发框架，核心组件包括：
1. Prompt Templates：模板化提示词
2. LLM Models：大语言模型封装
3. Output Parsers：输出解析器
4. Retriever：文档检索器
5. Chains：用 LCEL 管道符串联组件

LCEL 语法：chain = prompt | llm | parser
调用方式：chain.invoke(input)""",

    "rag.txt": """RAG 检索增强生成

RAG（Retrieval-Augmented Generation）是解决 LLM 幻觉问题的核心方案。

工作流程：
1. 用户提出问题
2. 检索器从知识库中找到相关文档片段
3. 将问题和文档片段一起发给 LLM
4. LLM 基于文档内容生成有据可依的回答

优势：减少幻觉、知识可更新、可追溯来源""",

    "embedding.txt": """Embedding 向量嵌入

Embedding 是将文本转换为数字向量的技术。
核心特性：语义相似的文本，向量距离更近。

常见模型：
- OpenAI text-embedding-3-small（1536维）
- BAAI/bge-small-zh-v1.5（中文开源，512维）
- GLM embedding-3（2048维）

余弦相似度：cos(θ) = A·B / (|A|·|B|)，范围[-1,1]""",
}


# ========== 阶段1：文档分块 ==========
print("=" * 60)
print("【阶段1：文档分块】")

all_chunks = []
all_metadatas = []

for filename, content in knowledge_docs.items():
    chunks = simple_splitter(content, chunk_size=150, overlap=30)
    for chunk in chunks:
        if len(chunk) > 20:  # 过滤太短的块
            all_chunks.append(chunk)
            all_metadatas.append({"source": filename})

print(f"  文档数: {len(knowledge_docs)}")
print(f"  分块后: {len(all_chunks)} 个块")
for i, (chunk, meta) in enumerate(zip(all_chunks, all_metadatas)):
    print(f"    [块{i+1}] {meta['source']}: {len(chunk)}字符 -> {chunk[:40]}...")
print()


# ========== 阶段2：存入向量库 ==========
print("=" * 60)
print("【阶段2：向量化 + 存入向量库】")

db = SimpleVectorDB()
ids = [f"chunk_{i}" for i in range(len(all_chunks))]
db.add(all_chunks, all_metadatas, ids)

print(f"  向量库文档数: {db.count()}")
print()


# ========== 阶段3：用户检索 ==========
print("=" * 60)
print("【阶段3：用户提问 -> 向量检索 -> 返回相关文档】")

test_queries = [
    "FastAPI 怎么安装？",
    "LCEL 是什么？",
    "RAG 的工作流程是怎样的？",
    "Embedding 模型有哪些推荐？",
    "如何减少 LLM 的幻觉？",
]

for query in test_queries:
    results = db.query(query, n_results=2)

    print(f"  Q: {query}")
    for doc, metadata, distance in zip(
        results["documents"],
        results["metadatas"],
        results["distances"],
    ):
        source = metadata["source"]
        print(f"    [{source}] 距离:{distance:.4f}")
        print(f"    {doc[:60]}...")
    print()


# ========== 总结 ==========
print("=" * 60)
print("【总结：Naive RAG 检索链路】")
print("""
  原始文档
      │  分块（chunk_size + chunk_overlap）
      ▼
  文本块列表
      │  Embedding（文本转向量）
      ▼
  向量数据库
      │
      ▼
  用户提问 -> Embedding -> 向量相似度检索 -> Top-K 相关文档

  下一步（Section 5）：相关文档 + 用户问题 -> LLM -> 生成回答
  生产升级（第2周）：Chroma/Milvus + 真实 Embedding 模型 + 混合检索 + Rerank
""")
