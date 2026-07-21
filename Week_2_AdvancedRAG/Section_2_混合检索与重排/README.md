# 第2周-Section_2：混合检索 + Rerank 重排

## 学习目标
- 理解为什么单一向量检索不够用
- 掌握 BM25 关键词检索原理
- 掌握混合检索（BM25 + 向量检索）的融合策略
- 掌握 Rerank 重排序的原理与实现

## 前置知识
- Section_1 的 Query Transformation
- FAISS 向量检索基础
- LangChain Retriever 接口

## 核心概念

### 1. 为什么需要混合检索？

单一向量检索的问题：
- **语义检索擅长**：用户问"怎么减肥"，能匹配到"控制饮食+运动"
- **关键词检索擅长**：用户问"Error 403 Forbidden"，需要精确匹配错误码

```
用户问题: "Python 3.12 match 语法"
  向量检索 → 可能匹配到"Python语法大全"（太泛）
  关键词检索 → 精确匹配"match语法"相关文档
  混合检索 → 两者结合，效果最好
```

### 2. BM25 关键词检索

**原理**：基于词频（TF）和逆文档频率（IDF）的经典检索算法。
- 词在文档中出现越多 → 越相关
- 词在整个语料库中越罕见 → 越有区分度

**优点**：精确匹配能力强，不需要 Embedding 模型
**缺点**：无法理解语义，"猫"和"猫咪"不会匹配

### 3. 混合检索融合策略

```
用户问题
  ├── BM25 检索 → Top-K 结果（带分数）
  └── 向量检索 → Top-K 结果（带分数）
         ↓
    融合排序（RRF / 加权）
         ↓
      最终 Top-K
```

**RRF（Reciprocal Rank Fusion）**：
```python
score = Σ 1 / (k + rank_i)
# k 通常取 60，rank_i 是文档在第 i 个检索器中的排名
```

### 4. Rerank 重排序

**原理**：用一个专门的 Cross-Encoder 模型，对候选文档和问题做精细打分。

```
检索阶段（召回）：快速粗筛 Top-20
    ↓
Rerank（精排）：Cross-Encoder 逐个打分 → 重排序 → 输出 Top-5
```

**为什么有效**：
- 检索阶段用的是 Bi-Encoder（快但粗糙）
- Rerank 用的是 Cross-Encoder（慢但精准）
- 两阶段组合：先粗筛再精排

## 代码运行方式

```bash
cd Week_2_AdvancedRAG/Section_2_混合检索与重排
pip install langchain langchain-openai langchain-community faiss-cpu rank_bm25 sentence-transformers
python demo1_hybrid_retrieval.py
python demo2_rerank.py
```

## 技术栈
| 组件 | 选型 | 说明 |
|------|------|------|
| LLM | GLM-4-Flash | 生成回答 |
| Embedding | BAAI/bge-small-zh-v1.5（本地） | 向量检索 |
| 关键词检索 | BM25（rank_bm25） | 精确匹配 |
| 融合策略 | RRF | Reciprocal Rank Fusion |
| Rerank | BAAI/bge-reranker-base（本地 Cross-Encoder） | 精排重排序 |

## 推荐复习
- Section_1 的 HyDE 和多查询改写
- Week_1 Section_4 的向量检索原理

## 下一节预告
Section_3：RAGAs、DeepEval RAG 自动化评估体系
