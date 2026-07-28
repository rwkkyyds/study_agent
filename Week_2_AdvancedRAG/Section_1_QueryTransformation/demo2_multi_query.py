"""
Demo2: 多查询改写（Multi-Query）检索
核心思路：把一个问题从多个角度改写，分别检索，合并去重结果
"""
import os

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from fastembed import TextEmbedding # 用于加载本地 BGE 模型生成 Embedding
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings # 定义适配器类用来适配 FastEmbed 的 Embedding 输出到 LangChain 接口

# ========== GLM API 配置 ==========
GLM_API_KEY = os.getenv("ZHIPU_API_KEY", "")
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== FastEmbed 适配 LangChain 接口 ==========
class FastEmbedEmbeddings(Embeddings):
    """用 fastembed 加载本地 BGE 模型，适配 LangChain Embeddings 接口"""

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self._model = TextEmbedding(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(v) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(list(self._model.embed([text]))[0])


# ========== 1. 准备文档库（比demo1更多样化） ==========
docs = [
    Document(page_content="RAG通过检索外部知识来增强LLM回答，核心组件包括：文档加载、文本分块、Embedding、向量库、检索器、LLM。", metadata={"source": "rag_arch"}),
    Document(page_content="向量数据库选型：FAISS适合本地实验，Milvus/Pinecone适合生产环境，Chroma适合轻量原型。", metadata={"source": "vector_db_compare"}),
    Document(page_content="RAG常见优化策略：查询改写、混合检索、重排序、上下文压缩、分块策略优化。", metadata={"source": "rag_optimization"}),
    Document(page_content="Embedding模型选型：OpenAI text-embedding-3-small性价比高，BGE系列支持中文更好。", metadata={"source": "embedding_model"}),
    Document(page_content="RAG评估指标：Faithfulness（忠实度）、Answer Relevancy（答案相关性）、Context Precision（上下文精确度）。", metadata={"source": "rag_eval"}),
    Document(page_content="LangChain LCEL链式调用：用 | 管道符连接组件，支持流式输出、批量处理、异步调用。", metadata={"source": "lcel"}),
    Document(page_content="FastAPI异步优势：async/await并发处理请求，适合I/O密集型的LLM调用场景。", metadata={"source": "fastapi_async"}),
    Document(page_content="Docker多阶段构建：第一阶段编译依赖，第二阶段复制产物，减小镜像体积。", metadata={"source": "docker_multi_stage"}),
]

# ========== 2. 创建向量库（用本地 BGE 模型） ==========
embeddings = FastEmbedEmbeddings("BAAI/bge-small-zh-v1.5")
vectorstore = FAISS.from_documents(documents=docs, embedding=embeddings) 
# vecctorstore 是 一个 FAISS 向量库对象，已经包含了文档的Embedding
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# ========== 3. 定义多查询改写链 ==========
multi_query_prompt = ChatPromptTemplate.from_template("""
你是一个AI助手，擅长从不同角度理解用户问题。
请将以下问题改写成3个不同角度的子问题，每个子问题单独一行，不要编号。

原始问题：{question}

改写后的3个子问题：
""")

llm = ChatOpenAI(
    model="glm-4-flash",
    openai_api_key=GLM_API_KEY,
    openai_api_base=GLM_BASE_URL,
    temperature=0.7,
)
multi_query_chain = multi_query_prompt | llm | StrOutputParser()

# ========== 4. 多查询检索 + 去重 ==========
def multi_query_retrieval(question: str):
    print(f"\n{'='*60}")
    print(f"原始问题: {question}")
    print(f"{'='*60}")

    # Step1: 生成多个子问题
    raw_output = multi_query_chain.invoke({"question": question}) #raw_output 是 LLM 生成的文本，包含3个子问题，每个子问题占一行
    sub_questions = [q.strip() for q in raw_output.strip().split("\n") if q.strip()]

    print(f"\n【Step1】改写后的子问题:")
    for i, q in enumerate(sub_questions, 1):
        print(f"  Q{i}: {q}")

    # Step2: 每个子问题分别检索
    all_docs = []
    print(f"\n【Step2】分别检索:")
    for i, q in enumerate(sub_questions, 1):
        results = retriever.invoke(q) #results 是一个 list[Document]，每个 Document 包含 page_content 和 metadata
        print(f"  Q{i} 检索到 {len(results)} 个文档")
        all_docs.extend(results)

    # Step3: 去重（基于page_content）
    seen = set()
    unique_docs = []
    for doc in all_docs:
        content_hash = hash(doc.page_content)
        if content_hash not in seen: # -O(1) 的去重效率
            seen.add(content_hash)
            unique_docs.append(doc) # unique_docs 是去重后的文档列表

    print(f"\n【Step3】合并去重结果（共{len(unique_docs)}个）:")
    for i, doc in enumerate(unique_docs, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:70]}...")

    return unique_docs # 返回最终的去重文档列表

# ========== 5. 对比：单查询 vs 多查询 ==========
def demo_comparison(question: str):
    print(f"\n{'#'*60}")
    print(f"# 对比演示")
    print(f"{'#'*60}")

    # 单查询
    print(f"\n【单查询检索】直接用原始问题:")
    single_results = retriever.invoke(question)
    for i, doc in enumerate(single_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:70]}...")
    print(f"  命中文档数: {len(single_results)}")

    # 多查询
    multi_results = multi_query_retrieval(question)
    print(f"\n  最终命中文档数: {len(multi_results)}")

# ========== 6. 运行 ==========
if __name__ == "__main__":
    demo_comparison("RAG系统有哪些优化方法？")
    print("\n\n[OK] 多查询改写演示完成！")
