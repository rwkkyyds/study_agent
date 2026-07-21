# Section 3：pgvector 向量扩展 — 让 PostgreSQL 原生支持向量检索

## 🎯 学习目标

1. 掌握 pgvector 扩展的安装与向量表设计
2. 理解 IVFFlat / HNSW 两种向量索引的原理与适用场景
3. 实现 PostgreSQL 内的 **混合检索**（全文检索 + 向量相似度）
4. 用 pgvector 替代 FAISS/Chroma，搭建 **PostgreSQL 原生 RAG**

## 📚 前置知识与学习顺序

| 顺序 | 文件 | 内容 | 核心技能 |
|------|------|------|----------|
| 1 | `demo1_pgvector_setup.py` | 扩展安装、向量表创建、相似度查询 | 向量字段DDL、距离算子 |
| 2 | `demo2_vector_index.py` | IVFFlat/HNSW 索引、参数调优、性能对比 | 索引选型、EXPLAIN ANALYZE |
| 3 | `demo3_hybrid_search.py` | 全文检索 + 向量检索 + RRF 融合 | 混合检索架构 |
| 4 | `demo4_pgvector_rag.py` | 端到端 RAG：文档→Embedding→pgvector→LLM | RAG 全链路 |

**前置条件：** 已完成 Section_1 (Redis) + Section_2 (PostgreSQL进阶)，熟悉 SQLAlchemy 和索引基础。

## 🚀 代码运行方式

```bash
# 1. 确保 PostgreSQL 已启动（Docker 或本地），密码 123456
# 2. 安装依赖
pip install pgvector sqlalchemy psycopg2-binary fastembed numpy

# 3. 按顺序运行
python demo1_pgvector_setup.py
python demo2_vector_index.py
python demo3_hybrid_search.py
python demo4_pgvector_rag.py
```

## ⚠️ 注意事项

- pgvector 是 PostgreSQL 扩展，需要 **超级用户权限** 执行 `CREATE EXTENSION vector`
- HNSW 索引构建比 IVFFlat 慢，但查询精度更高
- 向量维度（如 384/768/1536）建表时就固定，后续无法修改
- 混合检索的 RRF 融合权重需要根据业务场景调参

## 🔄 推荐复习内容

- Week_2 Section_2：混合检索与重排（BM25 + 向量 + RRF）
- Week_4 Section_2：PostgreSQL 索引类型与 EXPLAIN ANALYZE

## 📖 下一节学习预告

**Section_4 异步高并发**：FastAPI async/await 改造、asyncio 事件循环、高并发连接池优化
