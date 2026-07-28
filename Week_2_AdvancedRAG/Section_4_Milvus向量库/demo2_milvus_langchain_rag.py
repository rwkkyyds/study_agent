"""
Demo2: Milvus + LangChain RAG 集成（手写 VectorStore 适配器）
功能：文档分块 → Embedding → 存入 Milvus → LangChain 检索链 → GLM 回答
数据流：Documents → bge-small-zh Embedding → Milvus → Retriever → Prompt → GLM → 回答
依赖：pip install pymilvus langchain langchain-community langchain-openai fastembed
前提：docker compose up -d 启动 Milvus 服务
学习价值：理解 LangChain VectorStore 接口的本质（就是一个带 search 的存储）
"""
import os

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from typing import Any
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from fastembed import TextEmbedding
from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema


# ========== 配置 ==========
MILVUS_URI = "http://localhost:19530"
COLLECTION_NAME = "demo_rag_langchain"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
VECTOR_DIM = 512
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 1. FastEmbed 适配器（封装为 LangChain Embeddings 接口） ==========
class FastEmbedEmbeddings(Embeddings):
    """
    将 fastembed 封装为 LangChain 的 Embeddings 接口。
    LangChain 要求实现两个方法：
    - embed_documents(texts): 批量嵌入文档
    - embed_query(text): 嵌入单条查询
    """
    def __init__(self, model_name: str):
        super().__init__()
        self.model = TextEmbedding(model_name)
        print(f"[OK] Embedding 模型已加载: {model_name}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = list(self.model.embed(texts))
        return [list(v) for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        return list(list(self.model.embed([text]))[0]) 
        #eg: self.model.embed([text]) 返回 [[vector]]，需要取第一行 [0]，再转成 list
        #具体例子: self.model.embed(["hello"]) 返回 [[0.1, 0.2, ...]]，需要取第一行 [0]，再转成 list 
        #[0]不也是数组？
        # 是的，self.model.embed(["hello"]) 返回 [[0.1, 0.2, ...]]，
        # 这是一个二维数组。取第一行 [0] 后得到 [0.1, 0.2, ...]，这是一个一维数组。最后再转成 list 就是最终的向量列表。


# ========== 2. Milvus VectorStore 适配器 ==========
class MilvusVectorStore(VectorStore):
    """
    手写 Milvus 向量存储适配器，实现 LangChain VectorStore 接口。
    只需实现两个核心方法：
    - from_texts(): 从文本创建向量库（包括创建 Collection、索引、插入数据）
    - similarity_search(): 相似度搜索

    这展示了 LangChain VectorStore 的本质：一个带 search 接口的存储。
    """
    def __init__(self, client: MilvusClient, collection_name: str, embedding: Embeddings):
        self.client = client
        self.collection_name = collection_name
        self.embedding = embedding

    @classmethod
    def from_texts(
        cls,
        texts: list[str],
        embedding: Embeddings,
        metadatas: list[dict] | None = None,
        collection_name: str = "default",
        **kwargs: Any,
    ) -> "MilvusVectorStore":
        """从文本列表创建向量库（LangChain 标准接口）"""
        client = MilvusClient(uri=kwargs.get("uri", MILVUS_URI))

        # 清理旧 Collection
        if client.has_collection(collection_name):
            client.drop_collection(collection_name)

        # 创建 Schema
        schema = CollectionSchema(fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ])

        client.create_collection(collection_name=collection_name, schema=schema)

        # 创建 HNSW 索引
        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector", #指定向量字段
            index_type="HNSW",
            metric_type="COSINE", #指定使用余弦相似度进行搜索
            params={"M": 16, "efConstruction": 200}, # M 控制索引复杂度，efConstruction 控制构建质量
        )
        client.create_index(collection_name=collection_name, index_params=index_params)

        # 向量化并插入
        vectors = embedding.embed_documents(texts)
        if metadatas is None:
            metadatas = [{}] * len(texts)

        data = [
            {"text": t, "vector": v, "metadata": m}
            for t, v, m in zip(texts, vectors, metadatas)
        ]
        client.insert(collection_name=collection_name, data=data)

        # 加载到内存
        client.load_collection(collection_name)

        print(f"[OK] 已创建 MilvusVectorStore: {collection_name}, {len(texts)} 条文档")
        return cls(client=client, collection_name=collection_name, embedding=embedding)

    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> list[Document]:
        """相似度搜索（LangChain 标准接口）"""
        query_vector = self.embedding.embed_query(query)
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=k,
            output_fields=["text", "metadata"],
            search_params={"metric_type": "COSINE"}, #指定使用余弦相似度进行搜索
        )
        docs = []
        for hit in results[0]:
            docs.append(Document(
                page_content=hit["entity"]["text"],
                metadata=hit["entity"].get("metadata", {}),
            ))
        return docs

    def add_texts(self, texts: list[str], metadatas: list[dict] | None = None, **kwargs: Any) -> list[str]:
        """追加文本（LangChain 标准接口）"""
        vectors = self.embedding.embed_documents(texts)
        if metadatas is None:
            metadatas = [{}] * len(texts)   # [{}, {}, {}]
        data = [
            {"text": t, "vector": v, "metadata": m}
            for t, v, m in zip(texts, vectors, metadatas)
        ]
        result = self.client.insert(collection_name=self.collection_name, data=data)
        return result["ids"] 


# ========== 3. 准备知识文档 ==========
def prepare_documents() -> tuple[list[str], list[dict]]:
    """模拟 RAG 场景：准备一批知识文档"""
    texts = [
        "RAG（检索增强生成）是当前最主流的 LLM 应用架构。它通过检索外部知识库，将相关信息注入 Prompt，让大模型基于真实数据回答，大幅减少幻觉。",
        "HyDE（假设文档嵌入）是一种查询改写技术。先让 LLM 生成假设性回答，用回答的向量去检索真实文档，因为假设回答和真实文档在语义空间更接近。",
        "多查询改写（Multi-Query）让 LLM 从不同角度生成多个查询变体，分别检索后合并去重，能覆盖更多相关文档。",
        "BM25 是经典的稀疏检索算法，基于词频和逆文档频率计算相关性。擅长精确关键词匹配，但不理解语义。",
        "FAISS 是 Facebook 开源的向量检索库，支持多种索引类型。适合百万到千万级向量的本地检索，但没有持久化和分布式能力。",
        "Milvus 是生产级向量数据库，支持十亿级向量存储、分布式部署、多租户。适合企业级 RAG 系统的生产部署。",
        "Chroma 是轻量级向量数据库，API 简洁，适合快速原型开发。但性能和规模有限，不适合生产环境。",
        "ReAct（Reasoning + Acting）是 Agent 的核心范式。LLM 交替进行推理和行动，观察结果后继续推理，直到得出最终答案。",
        "Function Calling 是 OpenAI 提出的工具调用机制。LLM 输出结构化的函数调用参数，由外部代码执行后将结果返回 LLM。",
        "Agent Memory 包括短期记忆（对话上下文）和长期记忆（向量数据库存储的历史知识）。",
    ]
    metadatas = [
        {"source": "rag", "topic": "RAG概述"},
        {"source": "rag", "topic": "HyDE"},
        {"source": "rag", "topic": "Multi-Query"},
        {"source": "rag", "topic": "BM25"},
        {"source": "vector_db", "topic": "FAISS"},
        {"source": "vector_db", "topic": "Milvus"},
        {"source": "vector_db", "topic": "Chroma"},
        {"source": "agent", "topic": "ReAct"},
        {"source": "agent", "topic": "Function Calling"},
        {"source": "agent", "topic": "Memory"},
    ]
    print(f"[OK] 已准备 {len(texts)} 篇知识文档")
    return texts, metadatas


# ========== 4. 构建 RAG 检索链 ==========
def build_rag_chain(vectorstore: MilvusVectorStore):
    """
    构建 LangChain RAG 链：
    Retriever → 格式化上下文 → Prompt → GLM → 解析输出
    """
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) 
    #as_retriever() 是 LangChain VectorStore 的方法，返回一个 Retriever 对象，search_kwargs={"k": 3} 指定每次检索返回 3 条相关文档

    prompt = ChatPromptTemplate.from_template(
        "你是一个专业的技术助手。请根据以下参考资料回答用户问题。\n"
        "如果参考资料中没有相关信息，请明确说明'根据已有知识无法回答'。\n\n"
        "参考资料:\n{context}\n\n"
        "用户问题: {question}\n\n"
        "请用中文回答："
    )

    llm = ChatOpenAI(
        api_key=ZHIPU_API_KEY,
        base_url=ZHIPU_BASE_URL,
        model="glm-4-flash",
        temperature=0.7,
    )

    def format_docs(docs): #返回值 是一个字符串，格式化后的文档内容
        formatted = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "unknown")
            topic = doc.metadata.get("topic", "")
            formatted.append(f"[文档{i+1}] (来源: {source}, 主题: {topic})\n{doc.page_content}")
        return "\n\n".join(formatted)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )  #构建链路：先检索得到相关文档，格式化成字符串后填入 Prompt，再调用 LLM 生成回答，最后解析成纯文本输出

    print("[OK] RAG 检索链构建完成")
    print("     链路: 用户问题 → Milvus检索Top-3 → Prompt → GLM-4-Flash → 回答")
    return rag_chain, retriever


# ========== 5. 端到端问答测试 ==========
def run_qa_test(rag_chain, retriever):
    """测试 RAG 问答效果"""
    questions = [
        "什么是 RAG？它解决了什么问题？",
        "Milvus 和 FAISS 有什么区别？",
        "Agent 的 ReAct 范式是什么？",
        "量子计算的原理是什么？",  # 超出知识库范围
    ]

    for i, question in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"问题 {i+1}: {question}")
        print(f"{'=' * 60}")

        docs = retriever.invoke(question) #.invoke() 是 LangChain Retriever 的方法，执行检索并返回相关文档列表
        print(f"检索到 {len(docs)} 篇相关文档:")
        for j, doc in enumerate(docs):
            print(f"  [{j+1}] ({doc.metadata.get('topic', '?')}) {doc.page_content[:60]}...")

        print(f"\nGLM 回答:")
        answer = rag_chain.invoke(question) 
        #这里方进去的为什么不是检索后的docs？
        #因为rag_chain是build_rag_chain()函数中构建的链路，
        # 链路中已经包含了retriever，所以直接调用rag_chain.invoke(question)就会自动先执行检索，得到相关文档，再格式化文档内容，填入Prompt，最后调用LLM生成回答。
        print(f"  {answer}")


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        # Step 1: 准备文档
        texts, metadatas = prepare_documents()

        # Step 2: 初始化 Embedding
        embeddings = FastEmbedEmbeddings(EMBEDDING_MODEL)

        # Step 3: 创建 Milvus 向量库   
        vectorstore = MilvusVectorStore.from_texts(
            texts=texts,
            embedding=embeddings,
            metadatas=metadatas,
            collection_name=COLLECTION_NAME,
            uri=MILVUS_URI,
        )

        # Step 4: 构建 RAG 链
        rag_chain, retriever = build_rag_chain(vectorstore)

        # Step 5: 问答测试
        run_qa_test(rag_chain, retriever)

        print(f"\n{'=' * 60}")
        print("[OK] Milvus + LangChain RAG 集成演示完成！")
        print("核心收获：")
        print("  1. VectorStore 接口的本质 = 存储 + 搜索")
        print("  2. Milvus 替代 FAISS，支持生产级部署")
        print("  3. 整个 RAG 链路：文档 → 向量化 → Milvus → 检索 → LLM")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        print("[INFO] 请确保 Milvus 服务已启动（docker compose up -d）")
