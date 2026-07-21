# Section 5: 端到端 Naive RAG

## 学习目标
用 LangChain 现成组件把 RAG 全链路串起来：
- `Document` → `RecursiveCharacterTextSplitter` → FAISS → 检索 → `ChatPromptTemplate` | `ChatOpenAI` | `StrOutputParser` → 回答

## 前置知识
- Section 1: FastAPI 路由、Pydantic
- Section 2: LangChain Prompt/LLM/Parser/LCEL
- Section 3: 文档分块策略
- Section 4: Embedding + FAISS 向量库

## 代码运行方式
```bash
cd Week_1_NaiveRAG基础/Section_5_端到端NaiveRAG

# Demo 1: RAG 核心链路（LangChain 组件串联）
python demo1_rag_pipeline.py

# Demo 2: FastAPI 封装 RAG API
python demo2_rag_api.py
# 浏览器访问 http://127.0.0.1:8000/docs
```

## 用到的组件
| 组件 | 来源 | 作用 |
|------|------|------|
| `RecursiveCharacterTextSplitter` | langchain_text_splitters | 文档分块 |
| `Document` | langchain_core | 文档对象（text + metadata） |
| `ChatOpenAI` | langchain_openai | GLM 模型封装 |
| `ChatPromptTemplate` | langchain_core | Prompt 模板 |
| `StrOutputParser` | langchain_core | 输出解析 |
| `RunnablePassthrough` | langchain_core | LCEL 数据透传 |
| `FAISS` | faiss-cpu | 向量检索 |

## 注意事项
- GLM API Key 硬编码在代码中（与 Section 2 一致）
- Embedding 用哈希模拟（教学用），第2周换 OpenAI/BGE 真实模型
- `langchain_text_splitters` 降级到 0.3.11（高版本依赖 torch 有 DLL 问题）

## 推荐复习
- Section 2 的 LCEL 管道符语法
- Section 4 的 FAISS 向量检索流程

## 下一节预告
Section 6: Docker 打包部署 + 第1周 Demo 复盘
