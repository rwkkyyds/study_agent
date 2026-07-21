# 第2周-Section_1：Query Transformation

## 学习目标
- 理解为什么需要 Query Transformation
- 掌握 HyDE（假设性文档嵌入）原理与实现
- 掌握多查询改写（Multi-Query）策略
- 对比改写前后的检索效果差异

## 前置知识
- LangChain 核心组件（PromptTemplate, LCEL）
- Embedding 与向量检索基础
- RAG 基本链路（Week_1 已学）

## 核心概念

### 1. 为什么需要 Query Transformation？

用户问题 → 直接向量检索 → 效果不好，原因：
- 用户问题太短（如"什么是RAG？"），Embedding 语义信息少
- 用户表述和文档表述存在"语义鸿沟"
- 用户可能问的是模糊/多意图问题

**解决方案**：在检索前，先把问题"变换"成更适合检索的形式。

### 2. HyDE（Hypothetical Document Embeddings）

**核心思路**：让 LLM 先生成一个"假设性答案文档"，用这个文档去检索，而不是用原始问题。

```
用户问题: "什么是RAG？"
    ↓ LLM生成假设性文档
假设性文档: "RAG（检索增强生成）是一种结合外部知识库与大语言模型的技术..."
    ↓ 对假设性文档做Embedding
向量检索 → 找到真正相关的文档
```

**为什么有效**：假设性文档比原始问题更长、语义更丰富，和目标文档的向量更接近。

### 3. 多查询改写（Multi-Query）

**核心思路**：把一个问题从多个角度改写成多个子问题，分别检索，合并去重结果。

```
原始问题: "RAG有什么优缺点？"
    ↓ LLM改写
子问题1: "RAG的优势是什么？"
子问题2: "RAG的局限性有哪些？"
子问题3: "RAG在什么场景下表现不好？"
    ↓ 分别检索 + 合并去重
```

**为什么有效**：单一问题只能命中部分文档，多角度改写能扩大召回范围。

## 代码运行方式

```bash
cd Week_2_AdvancedRAG/Section_1_QueryTransformation
pip install langchain langchain-openai langchain-community faiss-cpu fastembed
python demo1_hyde.py
python demo2_multi_query.py
```

## 技术栈
| 组件 | 选型 | 说明 |
|------|------|------|
| LLM | GLM-4-Flash（智谱AI） | HyDE 生成假设文档 / 多查询改写 |
| Embedding | BAAI/bge-small-zh-v1.5（本地） | 通过 fastembed 加载，512维，支持中文 |
| 向量库 | FAISS（本地） | 适合实验环境，Week_1 已学 |

## 注意事项
- Embedding 用本地 BGE 模型（首次运行会自动下载约100MB）
- HyDE 会多调用一次 LLM，增加延迟和成本
- 多查询改写会调用多次检索，需要做结果去重
- LLM 调用需要 GLM API Key（代码中已配置）

## 推荐复习
- Week_1 Section_4 的 Embedding 原理
- Week_1 Section_5 的 RAG 链路

## 下一节预告
Section_2：混合检索 BM25+向量检索 + Rerank 重排
