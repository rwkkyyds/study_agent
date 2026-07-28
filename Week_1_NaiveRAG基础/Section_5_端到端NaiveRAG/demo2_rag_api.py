"""
Demo 2: FastAPI 封装 RAG API — 全用现成组件
运行方式：python demo2_rag_api.py
访问文档：http://127.0.0.1:8000/docs

接口：
  POST /query     — RAG 问答
  POST /documents — 上传文档
  GET  /health    — 健康检查
"""
import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough # 直接透传输入，不做修改
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import numpy as np
import faiss
import hashlib


# ========== Embedding ==========
def hash_embed(text: str, dim: int = 128) -> np.ndarray:
    h = hashlib.md5(text.encode()).digest()
    return np.array(
        [int.from_bytes(hashlib.md5(h + bytes([i])).digest()[:4], "little") / 2**32 * 2 - 1 for i in range(dim)],
        dtype=np.float32,
    )


# ========== 向量库管理 ==========
DIM = 128
index = faiss.IndexFlatIP(DIM) # FAISS 索引对象，使用内积作为相似度度量，适合小规模数据的暴力搜索
chunk_docs: list[Document] = []  # 存储 Document 对象
splitter = RecursiveCharacterTextSplitter(chunk_size=80, chunk_overlap=20) # 分块器，chunk_size 是块大小，chunk_overlap 是块之间的重叠部分


def rebuild_index():
    global index
    index = faiss.IndexFlatIP(DIM)
    if chunk_docs:
        vecs = np.array([hash_embed(d.page_content) for d in chunk_docs], dtype=np.float32)
        faiss.normalize_L2(vecs)
        index.add(vecs)


def retrieve(query: str, k: int = 3) -> list[Document]:
    if index.ntotal == 0:
        return []
    q = hash_embed(query).reshape(1, -1) # 将查询向量变成二维数组，适合 FAISS 输入
    faiss.normalize_L2(q)
    scores, idx = index.search(q, k=min(k, index.ntotal))
    return [
        Document(
            page_content=chunk_docs[i].page_content,
            metadata={**chunk_docs[i].metadata, "score": round(float(s), 4)},
        )
        for s, i in zip(scores[0], idx[0])
    ]


# ========== LLM + RAG 链 ==========
llm = ChatOpenAI(
    api_key=os.getenv("ZHIPU_API_KEY", ""),
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


rag_chain = (
    {"context": RunnablePassthrough() | (lambda q: retrieve(q)) | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
    | StrOutputParser()
)


# ========== Pydantic 模型 ==========
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)

class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]

class DocUpload(BaseModel): # 上传文档的请求体，包含文本内容和可选的来源信息
    content: str = Field(..., min_length=1)
    source: str = Field(default="upload")


# ========== FastAPI ==========
app = FastAPI(title="Naive RAG API", description="第1周 Demo：端到端 RAG")

DEFAULT_DOCS = [
    Document(page_content="FastAPI 是现代 Python Web 框架，基于 Starlette 和 Pydantic。支持异步，自动生成 API 文档。", metadata={"source": "fastapi.txt"}),
    Document(page_content="LangChain 是 LLM 应用框架。核心组件：Prompt Templates、LLM、Output Parsers、Retriever。LCEL 用管道符 | 串联。", metadata={"source": "langchain.txt"}),
    Document(page_content="RAG 让 LLM 先检索相关文档再生成回答，减少幻觉。流程：问题→检索→拼接Prompt→LLM→回答。", metadata={"source": "rag.txt"}),
    Document(page_content="Embedding 将文本转为向量，语义相似的文本向量距离更近。模型：OpenAI text-embedding-3-small、BGE-small-zh。", metadata={"source": "embedding.txt"}),
]


@app.on_event("startup")  # 应用启动时预加载一些默认文档，并构建向量索引
async def startup():
    for doc in DEFAULT_DOCS:
        chunk_docs.extend(splitter.split_documents([doc])) # 先分块再存储，chunk_docs 中存储的是分块后的 Document 对象
        #splitter.split_documents([doc])返回值是一个 Document 列表，每个 Document 是原文的一个块，metadata 中保留了原文的 source 信息
    rebuild_index()


@app.get("/health")
async def health():
    return {"status": "ok", "chunks": len(chunk_docs), "vectors": index.ntotal}


@app.post("/documents")
async def upload(doc: DocUpload): # 接收上传的文档，分块后加入向量库
    new_doc = Document(page_content=doc.content, metadata={"source": doc.source})
    new_chunks = splitter.split_documents([new_doc])
    chunk_docs.extend(new_chunks)
    rebuild_index()
    return {"added": len(new_chunks), "total": len(chunk_docs)}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if index.ntotal == 0:
        raise HTTPException(400, "知识库为空")
    docs = retrieve(req.question, req.top_k)
    context = format_docs(docs)
    answer = rag_chain.invoke(req.question)
    return QueryResponse(
        answer=answer,
        sources=[{"source": d.metadata["source"], "score": d.metadata.get("score", 0)} for d in docs],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
