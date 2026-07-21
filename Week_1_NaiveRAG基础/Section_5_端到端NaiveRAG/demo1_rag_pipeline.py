"""
Demo 1: 端到端 Naive RAG — 全用 LangChain 组件，不造轮子
运行方式：python demo1_rag_pipeline.py

数据流：文档 → RecursiveCharacterTextSplitter分块 → Embedding → FAISS → 检索 → GLM回答
"""

import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import numpy as np
import faiss
import hashlib


# ========== 1. 准备文档（用 LangChain Document 对象） ==========
print("=" * 60)
print("【1. 准备知识库文档】")

docs = [
    Document(
        page_content="FastAPI 是现代 Python Web 框架，基于 Starlette 和 Pydantic。"
                     "支持异步处理，自动生成 OpenAPI 文档。用 @app.get/@app.post 定义路由。"
                     "Pydantic BaseModel 做请求体校验。uvicorn main:app --reload 启动。",
        metadata={"source": "fastapi.txt"},
    ),
    Document(
        page_content="LangChain 是 LLM 应用开发框架。核心组件：Prompt Templates 模板化提示词、"
                     "LLM Models 模型封装、Output Parsers 输出解析、Retriever 检索器。"
                     "LCEL 语法：chain = prompt | llm | parser，用管道符串联组件。",
        metadata={"source": "langchain.txt"},
    ),
    Document(
        page_content="RAG（检索增强生成）让 LLM 先检索相关文档再生成回答，减少幻觉。"
                     "流程：用户提问→检索器找相关文档→拼接Prompt→LLM基于文档生成回答。"
                     "优势：知识可更新、可追溯来源。局限：检索质量直接影响回答质量。",
        metadata={"source": "rag.txt"},
    ),
    Document(
        page_content="Embedding 将文本转为向量，语义相似的文本向量距离更近。"
                     "常见模型：OpenAI text-embedding-3-small（1536维）、"
                     "BAAI/bge-small-zh-v1.5（中文开源512维）。"
                     "余弦相似度 cos(θ)=A·B/(|A|·|B|)，越接近1越相似。",
        metadata={"source": "embedding.txt"},
    ),
]
print(f"  文档数: {len(docs)}")
print()


# ========== 2. 分块（用 LangChain 组件） ==========
print("=" * 60)
print("【2. RecursiveCharacterTextSplitter 分块】")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=50,
    chunk_overlap=10,
    separators=["\n\n", "\n", "。", "，", " "],
)
chunks = splitter.split_documents(docs)
print(f"  分块后: {len(chunks)} 个块")
for i, chunk in enumerate(chunks):
    print(f"    [{i+1}] {chunk.metadata['source']}: {chunk.page_content[:45]}...")
print()


# ========== 3. Embedding + FAISS ==========
print("=" * 60)
print("【3. Embedding + FAISS 向量库】")


def hash_embed(text: str, dim: int = 128) -> np.ndarray:
    """哈希 Embedding（教学用，生产用 OpenAI/BGE）"""
    h = hashlib.md5(text.encode()).digest()
    return np.array(
        [int.from_bytes(hashlib.md5(h + bytes([i])).digest()[:4], "little") / 2**32 * 2 - 1 for i in range(dim)],
        dtype=np.float32,
    )


dim = 128
index = faiss.IndexFlatIP(dim)
vectors = np.array([hash_embed(c.page_content) for c in chunks], dtype=np.float32) # 文本转向量
faiss.normalize_L2(vectors) # 归一化，内积相当于余弦相似度
index.add(vectors) # 向量加入索引

print(f"  向量数: {index.ntotal}")
print()


# ========== 4. 检索器 ==========
print("=" * 60)
print("【4. 向量检索测试】")

def retrieve(query: str, k: int = 3) -> list[Document]:
    q = hash_embed(query).reshape(1, -1) #reshape(1, -1) 将查询向量变成二维数组，适合 FAISS 输入
    faiss.normalize_L2(q)
    scores, idx = index.search(q, k=k) # search 返回 (相似度数组, 索引数组)，这里检索最相似的 k 个块
    results = []
    for score, i in zip(scores[0], idx[0]):
        results.append(Document(
            page_content=chunks[i].page_content,
            metadata={**chunks[i].metadata, "score": round(float(score), 4)},
        ))
    return results


test_q = "FastAPI 怎么启动？"
print(f"  Q: {test_q}")
for doc in retrieve(test_q):
    print(f"    [{doc.metadata['source']}] {doc.metadata['score']} -> {doc.page_content[:50]}...")
print()


# ========== 5. RAG 链（LCEL） ==========
print("=" * 60)
print("【5. RAG 链 = 检索 | Prompt | GLM | Parser】")

llm = ChatOpenAI(
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    model="glm-4-flash",
    temperature=0.3,
)

rag_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是知识库问答助手。只根据参考资料回答，没有就直说。回答简洁。\n\n参考资料：\n{context}"),
    ("human", "{question}"),
])


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(f"[{d.metadata['source']}]\n{d.page_content}" for d in docs)


# LCEL 链：question → 检索 → 格式化 → Prompt → GLM → 文本
rag_chain = (
    {"context": RunnablePassthrough() | (lambda q: retrieve(q)) | format_docs, "question": RunnablePassthrough()} 
    # question 先透传给检索函数，再格式化成文本，q的传递流程：question → lambda q: retrieve(q) 和 question → format_docs-> context —> rag_prompt -> llm -> StrOutputParser -> 最终回答
    #为什么不是从左往右执行？因为 LCEL 的数据流是根据依赖关系自动推断的，
    # RunnablePassthrough() 只是一个占位符，真正的输入是 question 参数，
    # 链会自动把 question 传给 lambda q: retrieve(q)，然后把检索结果传给 format_docs，
    # 最后把格式化的文本传给 rag_prompt 的 context 参数。LCEL 会根据组件之间的数据依赖关系自动构建执行顺序，而不是简单的从左往右执行。
    | rag_prompt
    | llm
    | StrOutputParser()
)


# ========== 6. 端到端测试 ==========
print("=" * 60)
print("【6. RAG 问答测试】")
print()

for q in ["FastAPI 的主要特点是什么？", "RAG 的工作流程是怎样的？", "LCEL 语法是什么？", "有哪些常见的 Embedding 模型？"]:
    answer = rag_chain.invoke(question=q) # 直接调用链，输入 question 参数，链会自动处理检索、格式化、Prompt、LLM、解析等步骤，返回最终文本回答
    print(f"  Q: {q}")
    print(f"  A: {answer}")
    print()


print("=" * 60)
print("【总结】")
print("""
  索引：Document → RecursiveCharacterTextSplitter.split_documents() → FAISS
  查询：question → retrieve() → format_docs → Prompt | GLM | Parser → 回答

  用到的组件（全是现成的，没造轮子）：
    - RecursiveCharacterTextSplitter：LangChain 分块器
    - Document：LangChain 文档对象（text + metadata）
    - ChatOpenAI：LangChain LLM 封装
    - ChatPromptTemplate：LangChain Prompt 模板
    - StrOutputParser：LangChain 输出解析器
    - RunnablePassthrough：LCEL 数据透传
    - FAISS：Meta 向量检索库

  升级方向（第2周）：真实Embedding → 混合检索 → Rerank → Milvus
""")
