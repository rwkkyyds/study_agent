"""
Demo2: Rerank 重排序（真实 Cross-Encoder 模型）
核心思路：检索阶段粗筛 → Cross-Encoder 精排 → 输出最终结果
使用 BAAI/bge-reranker-base 本地模型，基于 sentence-transformers
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from fastembed import TextEmbedding
from sentence_transformers import CrossEncoder
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

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
    Document(page_content="RAG通过检索外部知识来增强LLM回答，核心组件包括：文档加载、文本分块、Embedding、向量库、检索器、LLM。", metadata={"source": "rag_arch.txt"}),
    Document(page_content="向量数据库选型：FAISS适合本地实验，Milvus/Pinecone适合生产环境，Chroma适合轻量原型。", metadata={"source": "vector_db_compare.txt"}),
    Document(page_content="RAG常见优化策略：查询改写、混合检索、重排序、上下文压缩、分块策略优化。", metadata={"source": "rag_optimization.txt"}),
    Document(page_content="Embedding模型选型：OpenAI text-embedding-3-small性价比高，BGE系列支持中文更好。", metadata={"source": "embedding_model.txt"}),
    Document(page_content="RAG评估指标：Faithfulness（忠实度）、Answer Relevancy（答案相关性）、Context Precision（上下文精确度）。", metadata={"source": "rag_eval.txt"}),
    Document(page_content="LangChain LCEL链式调用：用 | 管道符连接组件，支持流式输出、批量处理、异步调用。", metadata={"source": "lcel.txt"}),
    Document(page_content="FastAPI异步优势：async/await并发处理请求，适合I/O密集型的LLM调用场景。", metadata={"source": "fastapi_async.txt"}),
    Document(page_content="Docker多阶段构建：第一阶段编译依赖，第二阶段复制产物，减小镜像体积。", metadata={"source": "docker_multi_stage.txt"}),
    Document(page_content="BM25基于词频和逆文档频率，擅长关键词精确匹配，但无法理解语义。", metadata={"source": "bm25_intro.txt"}),
    Document(page_content="Cross-Encoder将问题和文档拼接后一起编码，能捕捉更细粒度的交互特征。", metadata={"source": "cross_encoder.txt"}),
]

# ========== 2. 创建向量检索器（粗筛） ==========
embeddings = FastEmbedEmbeddings("BAAI/bge-small-zh-v1.5")
vectorstore = FAISS.from_documents(documents=docs, embedding=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 10})  # 粗筛取 10 个

# ========== 3. 加载 Rerank 模型（精排） ==========
# BAAI/bge-reranker-base：Cross-Encoder 架构，将问题和文档拼接后一起编码
# 首次运行会自动下载模型（约 1.1GB），后续使用本地缓存
reranker = CrossEncoder("BAAI/bge-reranker-base", max_length=512)
# reranker是一个CrossEncoder模型对象，加载了BAAI/bge-reranker-base预训练模型，max_length=512表示输入文本的最大长度为512个token，超过部分会被截断。

def cross_encoder_rerank(
    question: str,
    docs: list[Document],  #粗筛得到的候选文档列表
    top_n: int = 5,
) -> list[Document]:
    """用 Cross-Encoder 对候选文档重排序"""
    # 构造 [question, document] 配对
    pairs = [[question, doc.page_content] for doc in docs]

    # Cross-Encoder 打分（返回每个配对的相关性分数）
    scores = reranker.predict(pairs)

    # 按分数降序排序
    scored_docs = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

    return [doc for doc, _ in scored_docs[:top_n]]


# ========== 4. 对比演示 ==========
def demo_comparison(question: str):
    print(f"\n{'='*60}")
    print(f"问题: {question}")
    print(f"{'='*60}")

    # 检索阶段：粗筛 Top-10
    candidates = retriever.invoke(question)
    print(f"\n【检索阶段】粗筛 Top-10:")
    for i, doc in enumerate(candidates, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:50]}...")

    # Rerank 阶段：Cross-Encoder 精排
    reranked = cross_encoder_rerank(question, candidates, top_n=5)
    print(f"\n【Rerank 精排】Cross-Encoder Top-5:")
    for i, doc in enumerate(reranked, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:50]}...")

    # 展示 Rerank 分数
    pairs = [[question, doc.page_content] for doc in candidates]
    scores = reranker.predict(pairs)
    scored = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    print(f"\n【Rerank 分数详情】:")
    for i, (doc, score) in enumerate(scored[:5], 1):
        print(f"  {i}. [{doc.metadata['source']}] score={score:.4f}")


# ========== 5. 运行 ==========
if __name__ == "__main__":
    demo_comparison("RAG系统有哪些优化方法？")
    demo_comparison("如何提高LLM应用的性能？")
    print("\n\n[OK] Rerank 重排序演示完成！")
