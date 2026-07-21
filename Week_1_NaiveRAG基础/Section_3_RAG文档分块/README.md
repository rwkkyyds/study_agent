# Section 3: RAG 文档加载与多格式文本分块策略

## 学习目标

- 理解为什么 RAG 需要文档加载和分块
- 掌握 LangChain 文档加载器（TextLoader、DirectoryLoader）
- 掌握 RecursiveCharacterTextSplitter 分块策略
- 理解 chunk_size 和 chunk_overlap 的影响

## 前置知识

- Section 1: FastAPI 基础
- Section 2: LangChain 核心组件（Prompt、LLM、Parser、LCEL）

## 学习顺序

1. 先运行 `demo1_doc_loader.py` — 文档加载（txt、模拟多格式）
2. 再运行 `demo2_text_splitter.py` — 分块策略对比
3. 最后运行 `demo3_chunk_pipeline.py` — 加载+分块完整流水线

## 代码运行方式

```bash
# 安装依赖
pip install langchain langchain-community

# 依次运行
python demo1_doc_loader.py
python demo2_text_splitter.py
python demo3_chunk_pipeline.py
```

## 注意事项

- 分块是 RAG 系统质量的关键环节，块太大/太小都会影响检索效果
- chunk_overlap 用于避免语义在块边界被截断

## 推荐复习内容

- LangChain 文档加载器：https://python.langchain.com/docs/integrations/document_loaders/
- TextSplitter 文档：https://python.langchain.com/docs/how_to/recursive_text_splitter/

## 下一节预告

**Section 4: Embedding 原理与本地向量库** — 向量嵌入、FAISS/Chroma 使用
