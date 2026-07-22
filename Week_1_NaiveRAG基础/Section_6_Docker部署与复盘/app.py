"""
第1周 Demo：Naive RAG API
融合 Section 1-6 所有知识点：
  - Section 1: FastAPI 路由、Pydantic 数据校验
  - Section 2: LangChain Prompt/LLM/Parser/LCEL
  - Section 3: RecursiveCharacterTextSplitter 分块
  - Section 4: FAISS 向量检索
  - Section 5: RAG 全链路整合
  - Section 6: Docker 部署

运行方式：python app.py
访问文档：http://127.0.0.1:8000/docs
"""

import logging
import hashlib
import numpy as np
import faiss
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ========== 日志（Section 1 学的） ==========
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
#asctime: 2024-06-01 12:00:00, levelname: INFO, message: "收到问题: 什么是 RAG?"
logger = logging.getLogger(__name__) 
# logger是一个日志记录器对象，可以用来输出日志信息。通过调用logger.info()、logger.error()等方法，
# 可以在控制台或日志文件中记录不同级别的日志消息，帮助开发者跟踪程序的运行状态和调试问题。


# ========== Embedding（Section 4 学的，教学用哈希模拟） ==========
def hash_embed(text: str, dim: int = 128) -> np.ndarray: #返回值是一个128维的numpy数组，表示输入文本的向量表示。
    """使用 MD5 哈希模拟文本嵌入（教学用，非语义向量）"""
    h = hashlib.md5(text.encode()).digest()
    return np.array(
        [int.from_bytes(hashlib.md5(h + bytes([i])).digest()[:4], "little") / 2**32 * 2 - 1 for i in range(dim)],
        dtype=np.float32,
    )


# ========== 向量库管理（Section 4 学的） ==========
DIM = 128
index = faiss.IndexFlatIP(DIM)
chunk_docs: list[Document] = []
splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=40)


def rebuild_index():
    """重建 FAISS 索引"""
    global index
    index = faiss.IndexFlatIP(DIM)
    if chunk_docs:
        vecs = np.array([hash_embed(d.page_content) for d in chunk_docs], dtype=np.float32)
        faiss.normalize_L2(vecs)
        index.add(vecs)
    logger.info(f"索引重建完成，向量数: {index.ntotal}")


def retrieve(query: str, k: int = 3) -> list[Document]:
    """向量检索（Section 4 学的）"""
    if index.ntotal == 0:
        return []
    q = hash_embed(query).reshape(1, -1) # q 是一个1行128列的二维numpy数组，表示输入查询的向量表示。reshape(1, -1)将其转换为适合FAISS输入的形状。
    faiss.normalize_L2(q)
    scores, idx = index.search(q, k=min(k, index.ntotal))
    return [
        Document(page_content=chunk_docs[i].page_content, metadata={**chunk_docs[i].metadata, "score": round(float(s), 4)})
        for s, i in zip(scores[0], idx[0])
    ]


# ========== LLM + RAG 链（Section 2 + Section 5 学的） ==========
llm = ChatOpenAI(
    api_key="70041ddde9824461bfb02fac3f469fc3.pDZCoxOgkovIx1vT",
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


# LCEL 链（Section 2 学的）
rag_chain = (
    {"context": RunnablePassthrough() | (lambda q: retrieve(q)) | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
    | StrOutputParser()
)


# ========== Pydantic 数据模型（Section 1 学的） ==========
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    top_k: int = Field(default=3, ge=1, le=10, description="检索文档数量")

class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]

class DocUpload(BaseModel):
    content: str = Field(..., min_length=1, description="文档内容")
    source: str = Field(default="upload", description="来源标识")


# ========== FastAPI 应用（Section 1 学的） ==========
app = FastAPI(title="Naive RAG API", description="第1周 Demo：端到端 Naive RAG 系统", version="1.0.0")

DEFAULT_DOCS = [
    Document(page_content="FastAPI 是现代 Python Web 框架，基于 Starlette 和 Pydantic。支持异步，自动生成 API 文档。", metadata={"source": "fastapi.txt"}),
    Document(page_content="LangChain 是 LLM 应用框架。核心组件：Prompt Templates、LLM、Output Parsers、Retriever。LCEL 用管道符 | 串联。", metadata={"source": "langchain.txt"}),
    Document(page_content="RAG 让 LLM 先检索相关文档再生成回答，减少幻觉。流程：问题→检索→拼接Prompt→LLM→回答。", metadata={"source": "rag.txt"}),
    Document(page_content="Embedding 将文本转为向量，语义相似的文本向量距离更近。模型：OpenAI text-embedding-3-small、BGE-small-zh。", metadata={"source": "embedding.txt"}),
]


@app.on_event("startup")
async def startup():
    """启动时加载默认知识库"""
    for doc in DEFAULT_DOCS:
        chunk_docs.extend(splitter.split_documents([doc]))
    rebuild_index()
    logger.info(f"默认知识库加载完成: {len(chunk_docs)} 个块")


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "chunks": len(chunk_docs), "vectors": index.ntotal}


@app.post("/documents")
async def upload(doc: DocUpload):
    """上传文档到知识库"""
    new_doc = Document(page_content=doc.content, metadata={"source": doc.source})
    new_chunks = splitter.split_documents([new_doc])
    chunk_docs.extend(new_chunks)
    rebuild_index()
    logger.info(f"文档上传: {doc.source}, 新增 {len(new_chunks)} 块")
    return {"added": len(new_chunks), "total": len(chunk_docs)}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """RAG 问答"""
    if index.ntotal == 0:
        raise HTTPException(400, "知识库为空，请先上传文档")
    logger.info(f"收到问题: {req.question}")
    docs = retrieve(req.question, req.top_k)
    answer = rag_chain.invoke(req.question)
    logger.info(f"回答完成，参考来源: {[d.metadata['source'] for d in docs]}")
    return QueryResponse(
        answer=answer,
        sources=[{"source": d.metadata["source"], "score": d.metadata.get("score", 0)} for d in docs],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
