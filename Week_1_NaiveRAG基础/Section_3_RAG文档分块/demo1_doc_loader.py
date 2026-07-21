"""
Demo 1: 文档加载器（Document Loader）
学习目标：理解 RAG 的第一步——把外部文档加载为 LangChain 可用的 Document 对象
运行方式：python demo1_doc_loader.py

RAG 的数据流：
  外部文档(txt/pdf/md) -> Document Loader -> Document对象列表 -> 分块 -> 向量化 -> 存储

Document 对象结构：
  - page_content: 文档文本内容（字符串）
  - metadata: 元数据（来源文件、页码等，字典）
"""

from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader, DirectoryLoader
import os
import tempfile


# ========== 1. 手动创建 Document 对象 ==========
# Document 是 LangChain 的标准文档格式，所有加载器最终都输出这个
print("=" * 60)
print("【1. Document 对象结构】")

doc = Document(
    page_content="FastAPI 是一个现代 Python Web 框架，支持异步处理。",
    metadata={"source": "fastapi_intro.txt", "page": 1}
)

print(f"  page_content: {doc.page_content}")
print(f"  metadata: {doc.metadata}")
print(f"  类型: {type(doc)}")
print()


# ========== 2. TextLoader 加载单个文本文件 ==========
print("=" * 60)
print("【2. TextLoader — 加载单个 .txt 文件】")

# 创建临时目录和示例文件
tmp_dir = tempfile.mkdtemp()
sample_file = os.path.join(tmp_dir, "sample.txt")
#生成临时文件 sample.txt 的完整路径，仅定义路径，并未实际创建文件。
with open(sample_file, "w", encoding="utf-8") as f:
    f.write("""第一章 FastAPI 入门

FastAPI 是一个用于构建 API 的现代、快速（高性能）的 Python Web 框架。
基于 Python 3.7+ 的标准类型提示，无需学习新语法。

主要特点：
1. 高性能：与 Node.js 和 Go 相当
2. 开发速度快：提升约 200%~300% 的开发速度
3. 更少的 Bug：减少约 40% 的人为错误
4. 自动文档：自动生成 Swagger UI 和 ReDoc

第二章 Pydantic 数据校验

Pydantic 是 Python 中最广泛使用的数据校验库。
FastAPI 深度集成了 Pydantic，用于请求体校验和响应模型定义。""")

# 用 TextLoader 加载
loader = TextLoader(sample_file, encoding="utf-8")
docs = loader.load()

print(f"  加载文件: sample.txt")
print(f"  loader类型: {type(loader)}")  # <class 'langchain_community.document_loaders.text_loader.TextLoader'>
print(f"  docs类型: {type(docs)}") # <class 'list'>
print(f"  文档数量: {len(docs)}")
print(f"  文档内容（前100字）: {docs[0].page_content[:100]}...")
print(f"  元数据: {docs[0].metadata}")
print()


# ========== 3. DirectoryLoader 批量加载目录 ==========
print("=" * 60)
print("【3. DirectoryLoader — 批量加载目录下所有文件】")

# 创建多个示例文件
files = {
    "rag_intro.txt": "RAG（检索增强生成）让 LLM 先检索相关文档，再基于文档生成回答。",
    "embedding.txt": "Embedding 将文本转换为向量，语义相似的文本向量距离更近。",
    "vector_db.txt": "向量数据库专门存储和检索向量，支持高效的相似度搜索。",
}

for filename, content in files.items():
    filepath = os.path.join(tmp_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

# DirectoryLoader 加载目录下所有 .txt 文件
# glob="*.txt" 表示只加载 .txt 文件
dir_loader = DirectoryLoader(
    tmp_dir,
    glob="*.txt",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"},
)
all_docs = dir_loader.load()

print(f"  目录: {tmp_dir}")
print(f"  加载文件数: {len(all_docs)}")
for i, doc in enumerate(all_docs):
    source = os.path.basename(doc.metadata.get("source", "unknown"))
    print(f"    [{i+1}] {source}: {doc.page_content[:50]}...")
print()


# ========== 4. 手动构建文档列表（模拟 PDF/Markdown 加载） ==========
print("=" * 60)
print("【4. 手动构建 Document — 模拟多格式加载】")
print("""
  实际项目中可能需要加载 PDF、Markdown、Word 等格式。
  每种格式有对应的 Loader：
    - PDF: PyPDFLoader, UnstructuredPDFLoader
    - Markdown: UnstructuredMarkdownLoader
    - Word: Docx2txtLoader
    - CSV: CSVLoader

  但核心输出都是一样的：List[Document]
""")

# 手动构建（模拟从不同格式加载的结果）
manual_docs = [
    Document(
        page_content="LangChain 是 LLM 应用开发框架，提供标准化组件。",
        metadata={"source": "langchain.md", "type": "markdown"}
    ),
    Document(
        page_content="Milvus 是开源向量数据库，支持十亿级向量检索。",
        metadata={"source": "milvus.pdf", "type": "pdf", "page": 5}
    ),
    Document(
        page_content="Docker 容器化部署确保环境一致性，是生产部署的标准方式。",
        metadata={"source": "deploy.docx", "type": "word"}
    ),
]

print(f"  手动构建文档数: {len(manual_docs)}")
for doc in manual_docs:
    src = doc.metadata["source"]
    print(f"    {src}: {doc.page_content}")
print()


# ========== 5. 清理临时文件 ==========
import shutil
shutil.rmtree(tmp_dir, ignore_errors=True)


# ========== 总结 ==========
print("=" * 60)
print("【总结】")
print("""
  1. Document = page_content(文本) + metadata(元数据)
  2. TextLoader: 加载单个文本文件
  3. DirectoryLoader: 批量加载目录下文件
  4. 不同格式有不同 Loader，但输出统一为 List[Document]
  5. 下一步：把 Document 切成小块（TextSplitter）
""")
