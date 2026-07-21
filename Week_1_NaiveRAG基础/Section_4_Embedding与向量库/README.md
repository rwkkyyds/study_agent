# Section 4: Embedding 原理与本地向量库

## 学习目标

- 理解 Embedding 的核心原理（文本 -> 向量）
- 掌握向量相似度计算（余弦相似度）
- 使用 Chroma 本地向量库存储和检索文档
- 完成 RAG 的"分块 -> 向量化 -> 存储 -> 检索"链路

## 前置知识

- Section 1-3: FastAPI、LangChain、文档加载与分块

## 学习顺序

1. `demo1_embedding_basics.py` — Embedding 原理与相似度计算
2. `demo2_chroma_vectordb.py` — Chroma 向量库基本操作
3. `demo3_rag_retrieval.py` — 完整的分块 + 向量化 + 检索链路

## 代码运行方式

```bash
pip install langchain-openai chromadb
python demo1_embedding_basics.py
python demo2_chroma_vectordb.py
python demo3_rag_retrieval.py
```

## 下一节预告

**Section 5: 端到端 Naive RAG** — 整合 FastAPI + LangChain 构建完整 RAG 系统
