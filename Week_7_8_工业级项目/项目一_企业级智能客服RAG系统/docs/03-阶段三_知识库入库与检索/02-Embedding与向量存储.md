# 02 Embedding 与向量存储

## 1. MockEmbedding

`app/rag/embeddings.py` 中的 `MockEmbedding` 使用 `SHA-256` 将文本和计数器映射为字节序列，再转换为浮点数并归一化。默认输出 768 维向量，无需网络访问或 API Key。

它的价值不是模拟真实语义，而是提供稳定的工程契约：

- `embed_query(text) -> list[float]`
- `embed_documents(texts) -> list[list[float]]`
- 维度固定
- 同一输入结果稳定
- 批量结果保持输入顺序

真实环境中应接入经过评估的 Embedding 模型，并通过配置选择 Provider，不能把 Mock 结果直接用于生产质量评估。

## 2. InMemoryVectorStore

`InMemoryVectorStore` 保存 `VectorRecord`：

- `id`：记录唯一标识，支持幂等覆盖写。
- `vector`：固定维度的浮点向量。
- `text`：切分块文本。
- `metadata`：文档 ID、来源、块序号等过滤和追踪信息。

搜索流程是：校验查询向量维度，计算余弦相似度，按分数倒序，再按 ID 稳定排序，最后截取 `top_k`。

## 3. 为什么先做适配器

直接在业务代码里调用 Milvus SDK 会导致：测试必须启动外部服务，业务层和基础设施强耦合，后续切换索引参数成本高。当前适配器先固定应用侧契约，阶段六再实现 Milvus Adapter 和持久化配置。

## 4. 生产替换要求

接入 Milvus 时至少补充：collection schema、向量维度配置、索引参数、租户或知识库隔离、upsert 幂等键、超时、重试、连接池、健康检查和迁移策略。不能仅将内存字典替换成 SDK 调用就宣称达到企业级生产标准。
