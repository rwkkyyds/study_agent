"""
Demo1: 混合检索（BM25 + 向量检索）+ RRF 融合
核心思路：BM25擅长关键词精确匹配，向量检索擅长语义匹配，融合后效果最好
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from fastembed import TextEmbedding
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever 
#这个包的作用是 提供BM25检索算法的实现，可以基于文档集合构建BM25索引，并进行关键词检索。
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings 
#这个包的作用是 定义了Embeddings类，作为文本向量化的接口规范，方便适配不同的Embedding模型（如OpenAI、FastEmbed等）并在系统中统一调用。
from langchain_core.retrievers import BaseRetriever 
#这个包的作用是提供检索器的基类，定义了检索器的接口规范，方便实现不同类型的检索器（如向量检索、BM25检索等）并在系统中统一调用。

# ========== GLM API 配置 ==========
GLM_API_KEY = "70041ddde9824461bfb02fac3f469fc3.pDZCoxOgkovIx1vT"
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== FastEmbed 适配 LangChain 接口 ==========
class FastEmbedEmbeddings(Embeddings):
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self._model = TextEmbedding(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(v) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(list(self._model.embed([text]))[0])


# ========== 1. 准备文档库 ==========
docs = [
    Document(page_content="RAG（检索增强生成）通过检索外部知识库来增强大模型的回答能力，减少幻觉。", metadata={"source": "rag_intro.txt"}),
    Document(page_content="向量数据库是RAG系统的核心组件，负责存储和检索文档的Embedding向量。", metadata={"source": "vector_db.txt"}),
    Document(page_content="LangChain是一个用于构建LLM应用的框架，提供了丰富的组件和链式调用能力。", metadata={"source": "langchain.txt"}),
    Document(page_content="FastAPI是一个高性能的Python Web框架，支持异步处理，适合构建API服务。", metadata={"source": "fastapi.txt"}),
    Document(page_content="Docker容器化技术可以将应用及其依赖打包，实现环境一致性和快速部署。", metadata={"source": "docker.txt"}),
    Document(page_content="BM25是一种基于词频和逆文档频率的经典检索算法，擅长关键词精确匹配。", metadata={"source": "bm25.txt"}),
    Document(page_content="Embedding将文本转换为向量，语义相近的文本向量距离更近。", metadata={"source": "embedding.txt"}),
    Document(page_content="Python 3.12 引入了 match 语句，支持模式匹配语法。", metadata={"source": "python_match.txt"}),
    Document(page_content="Python 的 GIL（全局解释器锁）限制了多线程并发性能。", metadata={"source": "python_gil.txt"}),
    Document(page_content="Pydantic 用于数据校验，通过类型注解自动验证输入数据。", metadata={"source": "pydantic.txt"}),
]

# ========== 2. 创建两种检索器 ==========

# BM25 关键词检索器
bm25_retriever = BM25Retriever.from_documents(documents=docs, k=5) 

# 向量检索器
embeddings = FastEmbedEmbeddings("BAAI/bge-small-zh-v1.5")
vectorstore = FAISS.from_documents(documents=docs, embedding=embeddings)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
#vector_retriever是基于FAISS向量数据库构建的检索器，search_kwargs={"k": 5}表示每次检索返回最相关的5个文档。
#返回值是一个Document对象列表，每个Document包含page_content（文档内容）和metadata（文档元数据，如来源）。


# ========== 3. RRF 融合检索 ==========
def rrf_fusion(
    retriever_results: list[list[Document]],
    k: int = 60, #k是RRF算法中的平滑常数，通常取60，可以根据实际情况调整。较大的k值会降低排名靠后的文档的影响，较小的k值会增加排名靠后的文档的影响。
    top_n: int = 5,
) -> list[Document]:
    """
    RRF (Reciprocal Rank Fusion) 融合多个检索器的结果
    公式: score = Σ 1 / (k + rank_i)
    k: 平滑常数，通常取 60
    """
    scores: dict[str, float] = {} 
    #scores是一个字典，用于存储每个文档的RRF分数，key是文档的唯一标识（这里用内容做去重key），value是该文档的RRF分数。初始时每个文档的分数为0.0。
    doc_map: dict[str, Document] = {}
    #doc_map是一个字典，用于存储文档的映射关系，key是文档的唯一标识（这里用内容做去重key），value是对应的Document对象。这个映射关系在计算RRF分数时用于快速查找Document对象。
    for results in retriever_results: #这个整体的作用是对多个检索器的结果进行融合，计算每个文档的RRF分数，并返回排名前top_n的文档列表。
        for rank, doc in enumerate(results):
            doc_id = doc.page_content  # 用内容做去重key
            if doc_id not in scores:
                scores[doc_id] = 0.0
                doc_map[doc_id] = doc
            scores[doc_id] += 1.0 / (k + rank)

    # 按 RRF 分数降序排序
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[doc_id] for doc_id, _ in sorted_docs[:top_n]] #返回排名前top_n的Document对象列表，doc_map[doc_id]用于根据文档唯一标识查找对应的Document对象。


# ========== 4. 对比演示 ==========
def demo_comparison(question: str):
    print(f"\n{'='*60}")
    print(f"问题: {question}")
    print(f"{'='*60}")

    # BM25 检索
    bm25_results = bm25_retriever.invoke(question)
    #返回值是一个Document对象列表，每个Document包含page_content（文档内容）和metadata（文档元数据，如来源）。这个列表是BM25检索器根据输入问题返回的最相关的5个文档。
    print(f"\n【BM25 关键词检索】Top-5:")
    for i, doc in enumerate(bm25_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:50]}...")

    # 向量检索
    vector_results = vector_retriever.invoke(question)
    #返回值是一个Document对象列表，每个Document包含page_content（文档内容）和metadata（文档元数据，如来源）。这个列表是向量检索器根据输入问题返回的最相关的5个文档。
    print(f"\n【向量语义检索】Top-5:")
    for i, doc in enumerate(vector_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:50]}...")

    # RRF 混合检索
    hybrid_results = rrf_fusion([bm25_results, vector_results], top_n=5)
    print(f"\n【RRF 混合检索】Top-5:")
    for i, doc in enumerate(hybrid_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:50]}...")


# ========== 5. 运行 ==========
if __name__ == "__main__":
    demo_comparison("Python 的 match 语法怎么用？")
    demo_comparison("RAG 系统怎么减少幻觉？")
    print("\n\n[OK] 混合检索对比演示完成！")
