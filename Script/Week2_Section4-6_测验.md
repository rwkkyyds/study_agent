# Week 2 Section 4-6 强制测验

**测验时间：** 2026-06-10
**测验范围：** Section 4 Milvus向量库 / Section 5 复杂文档解析 / Section 6 升级RAG系统
**总分：** 94/100

---

## 一、选择题（每题 5 分，共 30 分）

### 1. Milvus 中，HNSW 索引的 `M` 参数控制什么？

- A. 搜索时的候选集大小
- **B. 每个节点的最大连接数** ✓
- C. 索引构建时的线程数
- D. 向量维度

### 2. pymilvus 3.x 的 `MilvusClient` 和旧版 `Collection` API 的核心区别是？

- A. MilvusClient 不支持索引创建
- **B. MilvusClient 用 URI 连接，Collection 用 connect()** ✓
- C. MilvusClient 只支持 JSON 格式
- D. 没有区别

### 3. TextSplitter 和 Unstructured 的本质区别是？

- A. TextSplitter 更快
- **B. Unstructured 按元素类型解析，TextSplitter 按字符数切** ✓
- C. Unstructured 不支持表格
- D. TextSplitter 精度更高

### 4. 为什么表格必须整体保留不切碎？

- A. 切碎会增加存储空间
- **B. 切碎后行列关系丢失，LLM 无法做对比分析** ✓
- C. 切碎会导致向量维度不一致
- D. 切碎会触发 Milvus 报错

### 5. RRF 融合公式中 k=60 的作用是？

- A. 控制检索结果数量
- **B. 避免排名靠前的文档权重过大** ✓
- C. 设置向量维度
- D. 控制 BM25 的分词粒度

### 6. Advanced RAG 中 Rerank 的作用是？

- A. 替代向量检索
- **B. 对粗召回的 Top-K 结果做精排，提升精度** ✓
- C. 生成 Embedding 向量
- D. 替代 BM25 检索

**选择题得分：30/30**

---

## 二、简答题（每题 10 分，共 40 分）

### 7. 画出 Advanced RAG 的完整链路图（10/10） ✓

**答案：**
用户的问题 → BM25【关键字索引】+ Vector向量索引【Milvus】（混合索引） → RRF融合【两种不同索引的综合打分】 → Rerank【精排】 → 构造 Prompt → LLM → 回答

### 8. 解释 Milvus 的 `load_collection` 为什么必须在 `search` 之前调用（6/10）

**答案：**
因为 Milvus 的向量检索是在内存中进行的（内存快），需要将磁盘中的向量索引加载到内存中。

**扣分点：** 漏了关键点 —— 不调用 `load_collection` 直接 `search` 会**报错**，这是 API 的硬性要求，不是性能优化选择。

### 9. 表格转 Markdown 和转 HTML 哪个更适合 RAG 场景？为什么？（8/10）

**答案：**
Markdown 更适合表格场景：
1. 可以保留数据行
2. LLM 大模型内部对 Markdown 格式有大量训练，理解能力更强
3. 转成文本后可以向量化

HTML 适合精确场景。

**扣分点：** HTML 的适用场景在学习笔记中有提及（`<table>` 标签保留完整结构，适合需要精确解析的场景），回答中说"文档没有提及"不准确。

### 10. 什么是 Bi-Encoder 和 CrossEncoder？为什么 Rerank 用 CrossEncoder？（10/10） ✓

**答案：**
Bi-Encoder 是粗排序，CrossEncoder 是精排。Rerank 的场景需要精挑细选，所以用 CrossEncoder。

---

## 三、代码题（每题 15 分，共 30 分）

### 11. RRF 融合函数核心逻辑（15/15） ✓

```python
def rrf_fusion(results_list: list[list[Document]], k: int = 60) -> list[Document]:
    doc_scores = {}
    for results in results_list:
        for rank, doc in enumerate(results):
            doc_key = doc.page_content[:100]
            if doc_key not in doc_scores:
                doc_scores[doc_key] = {"doc": doc, "score": 0}
            doc_scores[doc_key]["score"] += 1 / (k + rank + 1)
    sorted_docs = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)
    return [item["doc"] for item in sorted_docs]
```

### 12. MilvusVectorStore 的 similarity_search 方法（15/15） ✓

```python
def similarity_search(self, query, k=4, **kwargs):
    qv = self.embedding.embed_query(query)
    results = self.client.search(
        collection_name=self.collection_name, data=[qv], limit=k,
        output_fields=["text", "metadata"],
        search_params={"metric_type": "COSINE"}
    )
    return [Document(page_content=hit["entity"]["text"],
                     metadata=hit["entity"].get("metadata", {})) for hit in results[0]]
```

---

## 总结

| 题型 | 得分 | 满分 |
|------|------|------|
| 选择题 | 30 | 30 |
| 简答题 | 34 | 40 |
| 代码题 | 30 | 30 |
| **总计** | **94** | **100** |

**与上次测验对比：** 70 分 → 94 分，提升 24 分。

**需要补强：** Milvus `load_collection` 是 API 硬性要求（不调用会报错），不仅仅是性能优化。
