# 第2周-Section_3：RAGAs、DeepEval RAG 自动化评估体系

## 学习目标
- 理解为什么需要 RAG 评估
- 掌握 RAGAs 评估框架的核心指标
- 掌握 DeepEval 评估框架的使用
- 对比两个框架的适用场景

## 前置知识
- Section_1 的 Query Transformation
- Section_2 的混合检索 + Rerank
- RAG 基本链路（Week_1）

## 核心概念

### 1. 为什么需要 RAG 评估？

RAG 系统搭好了，怎么知道它好不好？
- **人工评估**：准确但太慢、太贵、不可持续
- **自动化评估**：快速、可量化、可对比、可集成到 CI/CD

**评估维度**：
- 检索质量：找到的文档是否相关？
- 生成质量：LLM 的回答是否忠实于检索结果？

### 2. RAGAs 框架核心指标

RAGAs（Retrieval Augmented Generation Assessment）是 RAG 评估的标准框架。

| 指标 | 含义 | 评估什么 |
|------|------|----------|
| Faithfulness | 忠实度 | 回答是否基于检索到的文档（不编造） |
| Answer Relevancy | 答案相关性 | 回答是否切题 |
| Context Precision | 上下文精确度 | 检索到的文档中，相关文档的排名是否靠前 |
| Context Recall | 上下文召回率 | 相关文档是否都被检索到了 |

### 3. DeepEval 框架

DeepEval 是另一个 RAG 评估框架，特点：
- 支持多种评估指标（G-Eval、Faithfulness、Relevancy 等）
- 可集成到 pytest 测试框架
- 支持本地评估（不依赖外部 API）

## 代码运行方式

```bash
cd Week_2_AdvancedRAG/Section_3_RAG评估体系
pip install ragas deepeval langchain langchain-openai langchain-community faiss-cpu
python demo1_ragas_eval.py
python demo2_deepeval_eval.py
```

## 技术栈
| 组件 | 选型 | 说明 |
|------|------|------|
| 评估框架1 | RAGAs | RAG 标准评估框架 |
| 评估框架2 | DeepEval | 支持 pytest 集成 |
| LLM | GLM-4-Flash | 评估用 LLM |
| Embedding | BAAI/bge-small-zh-v1.5 | 本地 Embedding |

## 推荐复习
- Section_1 的 HyDE 和多查询改写
- Section_2 的混合检索 + Rerank

## 下一节预告
Section_4：Docker 部署 Milvus 生产级向量库 + Python SDK
