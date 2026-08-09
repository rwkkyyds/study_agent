# 阶段三：知识库入库与检索

> 把原始文本转换为可查询的向量记录，为阶段四客服工作流提供稳定、可替换的检索服务。

## 一、为什么阶段二之后做知识库检索

阶段二已经有了用户和文档相关的数据模型，但“有文档”不等于“能回答问题”。客服系统需要一条独立的检索链路：

```text
原始文档 → 文本分块 → Embedding → 向量存储 → Top-K 检索
```

本阶段先实现内核，而不急于绑定真实 Embedding API 或 Milvus。这样可以用确定性 Mock Embedding 完成测试，先把分块、维度、排序和结果契约理解清楚。

## 二、本阶段架构

```text
阶段四 Agent Tool / 业务入口
          │
          ▼
       Retriever
       │       │
       ▼       ▼
Embedding   VectorStore
 Provider    Adapter
       │       │
MockEmbedding  InMemoryVectorStore
```

`Retriever` 只负责组合两个能力：Embedding 把文本转换为向量，Vector Store 保存和搜索向量。后续替换为真实模型或 Milvus 时，上层工作流不需要复制检索逻辑。

## 三、完整数据链路

```text
原始文档
  │
  ▼
TextChunker.split_text
  │  固定窗口 + 重叠区间
  ▼
Chunk.content / chunk_index
  │
  ▼
MockEmbedding.embed_documents
  │
  ▼
VectorRecord
  │
  ▼
VectorStore.upsert

用户问题
  │
  ▼
MockEmbedding.embed_query
  │
  ▼
VectorStore.search
  │  余弦相似度 + Top-K
  ▼
RetrievedChunk
```

## 四、代码目录

- `app/rag/embeddings.py`：稳定生成固定维度归一化向量。
- `app/rag/vector_store.py`：内存向量记录、维度检查、覆盖写和相似度搜索。
- `app/rag/chunker.py`：固定大小和重叠切分。
- `app/rag/retriever.py`：组合 Embedding 与 Vector Store，返回领域结果。
- `tests/test_rag.py`：Embedding、分块、向量存储和 Retriever 测试。

## 五、关键设计原则

### 1. 确定性

同一文本在相同维度下生成相同向量，使测试和问题复现不依赖外部 API。

### 2. 快速失败

维度不一致、重叠长度非法和空查询在边界处立即抛出明确异常，而不是把错误带到深层搜索逻辑。

### 3. 可替换

应用层只依赖 `upsert` 和 `search` 等契约，不依赖内存字典的具体实现。生产环境可以替换 Milvus 适配器。

### 4. 元数据可追踪

`RetrievedChunk` 保留 `score` 和 `metadata`，便于回答中返回来源，也便于后续统计召回质量。

## 六、运行方式

```powershell
.venv\Scripts\python.exe -m pytest tests/test_rag.py -v
.venv\Scripts\python.exe -m pytest tests/ -v
```

## 七、当前边界

当前阶段不实现真实文件上传、Milvus 网络连接、LLM 生成和客服路由。阶段四会把 `Retriever` 注入客服工具，阶段五再在客服入口补充限流、会话记忆、指标和降级。

当前 `InMemoryVectorStore` 只适合本地开发和测试，不具备持久化、多副本和高可用能力。文档内容也不直接写入日志，不读取任意文件路径。

## 八、完成标准

- Mock Embedding 结果稳定且维度固定。
- TextChunker 可以生成重叠分块，并拒绝非法参数。
- VectorStore 执行维度校验、同 ID 覆盖和 Top-K 排序。
- Retriever 拒绝空查询，并返回稳定的 `RetrievedChunk`。
- 阶段三测试通过，阶段一和阶段二测试不回归。
