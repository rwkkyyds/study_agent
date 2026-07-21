"""
Demo 2: 文本分块策略（Text Splitter）
学习目标：理解为什么要分块、不同分块策略的区别、chunk_size 和 chunk_overlap 的影响
运行方式：python demo2_text_splitter.py

为什么要分块？
  - LLM 有上下文长度限制（如 4K/8K/128K tokens）
  - 向量检索的精度与块大小相关（太大=噪音多，太小=语义不完整）
  - 分块是 RAG 系统质量的关键调优点
"""

from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
)


# 准备测试文本
sample_text = """第一章 FastAPI 入门

FastAPI 是一个用于构建 API 的现代、快速的 Python Web 框架。基于 Python 3.7+ 的标准类型提示。

主要特点：
1. 高性能：与 Node.js 和 Go 相当
2. 开发速度快：提升约 200%~300% 的开发速度
3. 更少的 Bug：减少约 40% 的人为错误

第二章 Pydantic 数据校验

Pydantic 是 Python 中最广泛使用的数据校验库。FastAPI 深度集成了 Pydantic。

核心用法：
- BaseModel：定义数据模型
- Field：设置字段约束
- 自动校验：请求不符合规则时返回 422 错误

第三章 异步 I/O

async/await 是 Python 的异步编程范式。FastAPI 基于 ASGI 支持原生异步。

关键概念：
- async def：声明异步函数
- await：等待异步操作完成
- asyncio.sleep()：异步版本的 time.sleep()"""


# ========== 1. RecursiveCharacterTextSplitter（最常用） ==========
print("=" * 60)
print("【1. RecursiveCharacterTextSplitter — 最推荐的分块器】")
print("""
  工作原理：按分隔符优先级递归拆分
  优先级：\\n\\n（段落） -> \\n（换行） -> 句号 -> 空格 -> 字符

  为什么叫"递归"？
  如果一个块太大，就用下一级分隔符继续拆，直到块大小符合要求。
""")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,      # 每个块的最大字符数
    chunk_overlap=20,    # 相邻块重叠的字符数（避免语义截断）,eg: hello world -> chunk1: "hello w", chunk2: "o world" 
    #ai生成的文本可能会在块边界被截断，导致语义不完整。
    # 设置 chunk_overlap 可以让相邻块有重叠部分，确保关键信息不丢失。
    separators=["\n\n", "\n", "。", "，", " "],  # 分隔符优先级
)

chunks = splitter.split_text(sample_text)

print(f"  chunk_size=200, chunk_overlap=20")
print(f"  原文长度: {len(sample_text)} 字符")
print(f"  分块数量: {len(chunks)}")
print()
for i, chunk in enumerate(chunks):
    print(f"  --- 块{i+1}（{len(chunk)}字符）---")
    print(f"  {chunk}...")
    print()


# ========== 2. chunk_size 的影响 ==========
print("=" * 60)
print("【2. chunk_size 的影响】")

for size in [100, 200, 500]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=20,
    )
    chunks = splitter.split_text(sample_text) #分块后的文本列表
    print(f"  chunk_size={size}: {len(chunks)} 块, 平均{sum(len(c) for c in chunks)//len(chunks)}字符/块")

print("""
  chunk_size 太小（如 50）：语义碎片化，检索到的内容不完整
  chunk_size 太大（如 2000）：噪音多，检索精度下降
  经验值：200~1000 字符（中文场景），需要根据实际效果调优
""")
print()


# ========== 3. chunk_overlap 的作用 ==========
print("=" * 60)
print("【3. chunk_overlap 的作用】")
print("""
  问题：如果一句话被切断在两个块的边界，两个块都不完整

  示例文本："FastAPI 是一个现代 Web 械"
  chunk1: "...FastAPI 是一个"      <- 语义不完整
  chunk2: "现代 Web 框架..."        <- 语义不完整

  解决：overlap 让相邻块有重叠，确保关键信息不丢失

  chunk1: "...FastAPI 是一个现代"   <- 完整
  chunk2: "一个现代 Web 框架..."    <- 完整（重叠部分用灰色标注）
""")

# 对比有无 overlap
for overlap in [0, 50]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=150,
        chunk_overlap=overlap,
    )
    chunks = splitter.split_text(sample_text)
    print(f"  chunk_overlap={overlap}:")
    for i, chunk in enumerate(chunks):
        print(f"    块{i+1}: {chunk}")
    print()

print("  经验值：chunk_overlap = chunk_size 的 10%~20%")
print()


# ========== 4. Document 对象的分块 ==========
print("=" * 60)
print("【4. 对 Document 对象分块（保留元数据）】")
print("""
  实际 RAG 中，分块的对象是 Document，不是纯文本。
  分块后每块都会继承原文档的 metadata。
""")

docs = [
    Document(
        page_content=sample_text,
        metadata={"source": "tutorial.txt", "author": "AI助手"}
    ),
]

splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20,
)

# split_documents 对 Document 对象分块
doc_chunks = splitter.split_documents(docs) 
#返回一个新的 Document 列表，每个 Document 是一个块，
# 内容是原文档的一部分，元数据继承原文档的 metadata。

print(f"  原始文档数: {len(docs)}")
print(f"  分块后文档数: {len(doc_chunks)}")
print()
for i, chunk in enumerate(doc_chunks[:3]):
    print(f"  --- 块{i+1} ---")
    print(f"  内容: {chunk.page_content[:50]}...")
    print(f"  元数据: {chunk.metadata}")  # 自动继承原文档的 metadata
    print()


# ========== 5. 分块策略对比 ==========
print("=" * 60)
print("【5. 分块策略对比】")

strategies = {
    "RecursiveCharacter": RecursiveCharacterTextSplitter(
        chunk_size=200, chunk_overlap=20
    ),
    "Character(按换行)": CharacterTextSplitter(
        chunk_size=200, chunk_overlap=20, separator="\n"
    ),
}

for name, splitter in strategies.items():
    chunks = splitter.split_text(sample_text)
    avg_len = sum(len(c) for c in chunks) // len(chunks) if chunks else 0
    print(f"  {name}: {len(chunks)} 块, 平均 {avg_len} 字符/块")

print("""
  推荐：RecursiveCharacterTextSplitter
  - 按语义边界（段落->换行->句子）递归拆分
  - 保留更多语义完整性
  - 是 RAG 项目中最常用的分块器
""")
