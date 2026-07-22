"""
Demo1: RAGAs 评估框架
核心指标：Faithfulness、Answer Relevancy、Context Precision、Context Recall
注意：RAGAs 版本需与 langchain-community 兼容
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from datasets import Dataset # 用于构建评估数据集
from ragas import evaluate # RAGAs 评估函数
from ragas.metrics import ( # RAGAs 内置评估指标
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper # 将 LangChain LLM 包装为 RAGAs 兼容接口
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings # LangChain Embeddings 基类
from fastembed import TextEmbedding # 本地 BGE Embedding 模型

# ========== GLM API 配置 ==========
GLM_API_KEY = "70041ddde9824461bfb02fac3f469fc3.pDZCoxOgkovIx1vT"
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 1. 准备评估数据 ==========
# RAGAs 需要以下字段：
# - question: 用户问题
# - answer: LLM 生成的回答
# - contexts: 检索到的文档列表
# - ground_truth: 标准答案（用于计算 Context Recall）

eval_data = {
    "question": [
        "什么是RAG？",
        "RAG系统有哪些优化方法？",
        "如何选择向量数据库？",
    ],
    "answer": [
        "RAG（检索增强生成）是一种结合外部知识库与大语言模型的技术，通过检索相关文档来增强LLM的回答能力，减少幻觉。",
        "RAG系统的优化方法包括：查询改写（HyDE、多查询改写）、混合检索（BM25+向量检索）、重排序（Cross-Encoder）、上下文压缩等。",
        "选择向量数据库需要考虑：数据规模（FAISS适合小规模、Milvus适合大规模）、是否需要持久化、是否需要分布式、部署复杂度等因素。",
    ],
    "contexts": [
        ["RAG（检索增强生成）通过检索外部知识库来增强大模型的回答能力，减少幻觉。"],
        ["RAG常见优化策略：查询改写、混合检索、重排序、上下文压缩、分块策略优化。", "BM25基于词频和逆文档频率，擅长关键词精确匹配。"],
        ["向量数据库选型：FAISS适合本地实验，Milvus/Pinecone适合生产环境，Chroma适合轻量原型。"],
    ],
    "ground_truth": [
        "RAG（Retrieval-Augmented Generation）是检索增强生成技术，通过检索外部知识库来增强大模型回答，减少幻觉。",
        "RAG优化方法包括查询改写、混合检索、重排序、上下文压缩、分块策略优化等。",
        "向量数据库选型：FAISS适合本地实验，Milvus/Pinecone适合生产环境，Chroma适合轻量原型。",
    ],
}

dataset = Dataset.from_dict(eval_data)


# ========== 本地 BGE Embedding 适配 LangChain 接口 ==========
class FastEmbedEmbeddings(Embeddings):
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self._model = TextEmbedding(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(v) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(list(self._model.embed([text]))[0])


# ========== 2. 配置评估用的 LLM 和 Embedding ==========
llm = ChatOpenAI(
    model="glm-4-flash",
    openai_api_key=GLM_API_KEY,
    openai_api_base=GLM_BASE_URL,
    temperature=0,
)

# 用本地 BGE 模型替代 GLM Embedding API
embeddings = FastEmbedEmbeddings("BAAI/bge-small-zh-v1.5")

# 包装为 RAGAs 兼容格式
wrapped_llm = LangchainLLMWrapper(llm)
wrapped_embeddings = LangchainEmbeddingsWrapper(embeddings)


# ========== 3. 运行 RAGAs 评估 ==========
def run_ragas_evaluation():
    print("=" * 60)
    print("RAGAs 评估开始")
    print("=" * 60)

    result = evaluate(
        dataset=dataset,
        metrics=[ # 选择评估指标
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=wrapped_llm,
        embeddings=wrapped_embeddings,
    )

    print("\n【评估结果】")
    print(result)

    df = result.to_pandas() # 转换为 DataFrame 以便更好展示和分析
    print("\n【详细结果（DataFrame）】")
    print(df.to_string())

    print("\n【平均分】")
    for col in df.columns:
        if df[col].dtype in ['float64', 'float32']:
            print(f"  {col}: {df[col].mean():.4f}")


if __name__ == "__main__":
    run_ragas_evaluation()
    print("\n\n[OK] RAGAs 评估演示完成！")
