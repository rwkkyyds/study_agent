# 阶段三：知识库入库与检索

## 阶段目标

建立一个不依赖外部 API Key、可测试、可替换存储后端的 RAG 检索内核，为阶段四客服工作流提供稳定的检索服务。

## 学习与阅读顺序

1. `01-阶段三概述.md`：理解边界、分层和请求链路。
2. `02-Embedding与向量存储.md`：理解向量生成与存储适配器。
3. `03-文本分块与检索服务.md`：理解分块、索引和查询流程。
4. `04-测试与企业化演进.md`：运行测试并了解生产替换路线。

## 代码目录

- `app/rag/embeddings.py`：`MockEmbedding`，稳定生成 768 维归一化向量。
- `app/rag/vector_store.py`：`InMemoryVectorStore`，通过余弦相似度完成 Top-K 搜索。
- `app/rag/chunker.py`：`TextChunker`，固定窗口和重叠切分。
- `app/rag/retriever.py`：`Retriever`，组合 Embedding 与 Vector Store。
- `tests/test_rag.py`：阶段三单元测试和服务级测试。

## 运行方式

在项目根目录执行：

```powershell
python -m pytest tests/test_rag.py -v
python -m pytest tests/ -v
```

## 企业级边界

当前实现只负责检索内核，不负责 HTTP 路由、数据库写入和 LLM 生成。这样阶段四可以将 `Retriever` 作为 Agent Tool 注入，阶段五再接入 Redis 缓存、限流、监控和降级。

生产环境将 `InMemoryVectorStore` 替换为 Milvus 适配器，保持 `upsert` 与 `search` 的应用层契约不变。当前本地替身用于快速测试，不宣称具备持久化、高可用或多副本能力。

## 完成标准

- Mock Embedding 结果确定且维度固定。
- 分块参数非法时快速失败。
- 向量存储执行维度校验、覆盖写和 Top-K 排序。
- Retriever 拒绝空查询，并返回稳定的领域结果。
- 阶段三测试全部通过，且阶段一、二测试不回归。
