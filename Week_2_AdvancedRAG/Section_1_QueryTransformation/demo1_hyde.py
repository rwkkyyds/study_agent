"""
Demo1: HyDE（假设性文档嵌入）检索
核心思路：让LLM先生成假设性答案，用答案去检索，而不是用问题
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8") # 解决中文输出乱码问题

from fastembed import TextEmbedding   # 用于加载本地 BGE 模型生成 Embedding
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings # 定义适配器类用来适配 FastEmbed 的 Embedding 输出到 LangChain 接口

# ========== GLM API 配置 ==========
GLM_API_KEY = "70041ddde9824461bfb02fac3f469fc3.pDZCoxOgkovIx1vT"
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== FastEmbed 适配 LangChain 接口 ==========
class FastEmbedEmbeddings(Embeddings):
    """用 fastembed 加载本地 BGE 模型，适配 LangChain Embeddings 接口"""

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"): 
        self._model = TextEmbedding(model_name) # 加载本地 BGE 模型

    def embed_documents(self, texts: list[str]) -> list[list[float]]:  # 返回 list[list[float]] 以适配 FAISS 的输入要求
        return [list(v) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(list(self._model.embed([text]))[0]) #list(self._model.embed([text]))[0] 是一个 numpy array，转换成 list 以适配 FAISS 的输入要求


# ========== 1. 准备模拟文档库 ==========
docs = [
    Document(page_content="RAG（检索增强生成）通过检索外部知识库来增强大模型的回答能力，减少幻觉。", metadata={"source": "rag_intro"}),
    Document(page_content="向量数据库是RAG系统的核心组件，负责存储和检索文档的Embedding向量。", metadata={"source": "vector_db"}),
    Document(page_content="LangChain是一个用于构建LLM应用的框架，提供了丰富的组件和链式调用能力。", metadata={"source": "langchain"}),
    Document(page_content="Embedding是将文本转换为高维向量的技术，语义相近的文本在向量空间中距离更近。", metadata={"source": "embedding"}),
    Document(page_content="FastAPI是一个高性能的Python Web框架，支持异步处理，适合构建API服务。", metadata={"source": "fastapi"}),
    Document(page_content="Docker容器化技术可以将应用及其依赖打包，实现环境一致性和快速部署。", metadata={"source": "docker"}),
]

# ========== 2. 创建向量库（用本地 BGE 模型） ==========
embeddings = FastEmbedEmbeddings("BAAI/bge-small-zh-v1.5")
vectorstore = FAISS.from_documents(documents=docs, embedding=embeddings) 
# 创建FAISS向量库并生成文档的Embedding,  from_documents方法会调用 FastEmbedEmbeddings 的 embed_documents 方法来生成文档的Embedding
retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) # 创建检索器，设置每次检索返回3条最相关的文档

# ========== 3. 定义 HyDE 链 ==========
# HyDE核心：先让LLM生成假设性文档
hyde_prompt = ChatPromptTemplate.from_template("""
请根据以下问题，写一段可能包含答案的技术文档内容（约100字）。
不需要准确，只需要看起来像是回答这个问题的文档段落。

问题：{question}

假设性文档：
""")

llm = ChatOpenAI(
    model="glm-4-flash",
    openai_api_key=GLM_API_KEY,
    openai_api_base=GLM_BASE_URL,
    temperature=0.7,
)
hyde_chain = hyde_prompt | llm | StrOutputParser()

# ========== 4. 对比：直接检索 vs HyDE检索 ==========
def demo_comparison(question: str):
    print(f"\n{'='*60}")
    print(f"用户问题: {question}")
    print(f"{'='*60}")

    # 方式1: 直接用问题检索
    print("\n【直接检索】用原始问题:")
    direct_results = retriever.invoke(question) 
    #direct_results 是一个 list[Document]，每个 Document 包含 page_content 和 metadata
    for i, doc in enumerate(direct_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:60]}...")

    # 方式2: HyDE检索
    print("\n【HyDE检索】先生成假设性文档:")
    hypothetical_doc = hyde_chain.invoke({"question": question})
    print(f"  假设性文档: {hypothetical_doc[:100]}...")

    hyde_results = retriever.invoke(hypothetical_doc)
    print(f"\n  用假设性文档检索到:")
    for i, doc in enumerate(hyde_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:60]}...")

# ========== 5. 运行对比 ==========
if __name__ == "__main__":
    demo_comparison("什么是RAG？")
    demo_comparison("如何部署LLM应用？")
    print("\n\n[OK] HyDE 对比演示完成！")
