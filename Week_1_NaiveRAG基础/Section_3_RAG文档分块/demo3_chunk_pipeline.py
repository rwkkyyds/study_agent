"""
Demo 3: 完整的文档加载 + 分块流水线
学习目标：把 Document Loader 和 Text Splitter 串联成完整的数据处理链
运行方式：python demo3_chunk_pipeline.py

完整 RAG 数据流：
  原始文档 -> 加载 -> 分块 -> 向量化(Embedding) -> 存储(向量数据库) -> 检索 -> LLM回答
  本节覆盖前两步：加载 + 分块
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
import tempfile


# ========== 模拟一个小型知识库 ==========
knowledge_sources = {
    "fastapi.txt": """FastAPI 入门指南

FastAPI 是一个现代 Python Web 框架，基于 Starlette 和 Pydantic。
主要特点：高性能、自动文档、类型安全。

安装方式：pip install fastapi uvicorn
最简示例：
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

运行命令：uvicorn main:app --reload
访问文档：http://127.0.0.1:8000/docs""",

    "langchain.txt": """LangChain 核心组件

LangChain 是 LLM 应用开发框架，核心组件包括：
1. Prompt Templates：模板化提示词
2. LLM Models：大语言模型封装
3. Output Parsers：输出解析器
4. Retriever：文档检索器
5. Chains：用 LCEL 管道符串联组件

LCEL 语法：chain = prompt | llm | parser
调用方式：chain.invoke(input)""",

    "rag_concept.txt": """RAG 检索增强生成

RAG（Retrieval-Augmented Generation）是解决 LLM 幻觉问题的核心方案。

工作流程：
1. 用户提出问题
2. 检索器从知识库中找到相关文档片段
3. 将问题和文档片段一起发给 LLM
4. LLM 基于文档内容生成有据可依的回答

优势：
- 减少幻觉：回答基于真实文档
- 知识可更新：更新文档即可，不需要重新训练模型
- 可追溯：可以标注回答来源""",

    "embedding.txt": """Embedding 向量嵌入

Embedding 是将文本转换为数字向量的技术。
核心特性：语义相似的文本，向量距离更近。

常见模型：
- OpenAI text-embedding-3-small
- BAAI/bge-small-zh-v1.5（中文开源）
- sentence-transformers/all-MiniLM-L6-v2

使用方式：
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings()
vector = embeddings.embed_query("什么是RAG")""",
}


# ========== 1. 文档加载阶段 ==========
print("=" * 60)
print("【阶段1：文档加载】")

# 创建临时目录，写入知识库文件
tmp_dir = tempfile.mkdtemp()
for filename, content in knowledge_sources.items():
    filepath = os.path.join(tmp_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

# 批量加载
from langchain_community.document_loaders import DirectoryLoader, TextLoader

loader = DirectoryLoader(
    tmp_dir,
    glob="*.txt",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"},
)
raw_docs = loader.load() #返回一个 Document 列表，
#每个 Document 包含 page_content 和 metadata（如 source 文件名）

print(f"  加载文件数: {len(raw_docs)}")
for doc in raw_docs:
    source = os.path.basename(doc.metadata["source"])
    print(f"    {source}: {len(doc.page_content)} 字符")
print()


# ========== 2. 分块阶段 ==========
print("=" * 60)
print("【阶段2：文本分块】")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=150,
    chunk_overlap=30,
    separators=["\n\n", "\n", "。", "，", " "],
)

chunked_docs = splitter.split_documents(raw_docs) 
#对 Document 列表进行分块，返回新的 Document 列表，
# 每个 Document 是一个块，内容是原文档的一部分，元数据继承原文档的 metadata。

print(f"  分块器: RecursiveCharacterTextSplitter")
print(f"  chunk_size=150, chunk_overlap=30")
print(f"  原始文档: {len(raw_docs)} 个")
print(f"  分块后: {len(chunked_docs)} 个块")
print()

# 展示分块结果
for i, chunk in enumerate(chunked_docs):
    source = os.path.basename(chunk.metadata.get("source", "unknown"))
    print(f"  [块{i+1}] 来源:{source} | {len(chunk.page_content)}字符")
    print(f"    {chunk.page_content[:80]}...")
    print()


# ========== 3. 分块质量分析 ==========
print("=" * 60)
print("【阶段3：分块质量分析】")

# 统计每个源文件的分块数
from collections import Counter
source_counts = Counter() 
for chunk in chunked_docs:
    source = os.path.basename(chunk.metadata.get("source", "unknown"))
    source_counts[source] += 1

print("  各文件分块分布:")
for source, count in source_counts.most_common(): #.most_common() 按照分块数降序排序
    print(f"    {source}: {count} 块")

# 块大小分布
sizes = [len(c.page_content) for c in chunked_docs]
print(f"\n  块大小统计:")
print(f"    最小: {min(sizes)} 字符")
print(f"    最大: {max(sizes)} 字符")
print(f"    平均: {sum(sizes)//len(sizes)} 字符")
print(f"    中位: {sorted(sizes)[len(sizes)//2]} 字符")
print()


# ========== 4. 检索预览（用简单关键词匹配模拟） ==========
print("=" * 60)
print("【阶段4：检索预览 — 分块后如何被检索到】")

def simple_search(query: str, docs: list, top_k: int = 2):
    """简单关键词检索（模拟 Retriever 行为）"""
    scored = []
    keywords = query.lower().split()
    for doc in docs:
        content_lower = doc.page_content.lower() #lower() 将文本转换为小写，
        #确保关键词匹配不区分大小写。
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: -x[0])
    return scored[:top_k]

queries = ["FastAPI 怎么安装", "RAG 的工作流程", "Embedding 模型推荐"]

for query in queries:
    results = simple_search(query, chunked_docs)
    print(f"  Q: {query}")
    for score, doc in results:
        source = os.path.basename(doc.metadata.get("source", "unknown"))
        print(f"    [{source}] 相关度:{score} -> {doc.page_content[:60]}...")
    print()


# ========== 5. 清理 ==========
import shutil
shutil.rmtree(tmp_dir, ignore_errors=True)


# ========== 总结 ==========
print("=" * 60)
print("【总结：完整的文档处理流水线】")
print("""
  原始文档 (.txt/.pdf/.md)
      │
      ▼
  Document Loader (TextLoader/DirectoryLoader)
      │
      ▼
  List[Document]  (page_content + metadata)
      │
      ▼
  Text Splitter (RecursiveCharacterTextSplitter)
      │
      ▼
  List[Document]  (分块后的文档，保留元数据)
      │
      ▼
  Embedding (下一节学)
      │
      ▼
  Vector Database (下一节学)
""")
