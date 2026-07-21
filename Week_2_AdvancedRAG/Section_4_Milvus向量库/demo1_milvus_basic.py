"""
Demo1: Milvus 基础操作（使用 MilvusClient 新 API）
功能：连接 Milvus → 创建 Collection → 插入向量 → 相似度搜索 → 过滤搜索 → 删除
依赖：pip install pymilvus fastembed
前提：docker compose up -d 启动 Milvus 服务
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8") # 解决 Windows 控制台乱码问题

from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema 
#DataType 是 MilvusClient 定义的数据类型枚举，CollectionSchema 和 FieldSchema 用于定义 Collection 的 Schema
from fastembed import TextEmbedding

# ========== 配置 ==========
MILVUS_URI = "http://localhost:19530"  # Milvus 服务地址
COLLECTION_NAME = "demo_rag_docs"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"  # 中文小模型，512维 
VECTOR_DIM = 512


# ========== 1. 连接 Milvus ==========
def connect_milvus() -> MilvusClient:
    """使用 MilvusClient 连接（pymilvus 3.x 推荐方式）"""
    client = MilvusClient(uri=MILVUS_URI)
    print(f"[OK] 已连接 Milvus: {MILVUS_URI}")
    return client


# ========== 2. 创建 Collection ==========
def create_collection(client: MilvusClient):
    """
    创建 Collection + 向量索引
    需要手动定义 Schema，因为要包含 text/source 自定义字段
    """
    # 如果已存在则删除（方便重复运行）
    if client.has_collection(COLLECTION_NAME):
        client.drop_collection(COLLECTION_NAME)
        print(f"[INFO] 已删除旧 Collection: {COLLECTION_NAME}")

    # 定义 Schema（手动指定所有字段）
    schema = CollectionSchema(fields=[
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
    ], description="RAG demo collection")

    # 创建 Collection
    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
    )

    # 创建向量索引（HNSW：适合中小规模高召回场景）
    index_params = client.prepare_index_params() # 创建索引参数对象
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",
        metric_type="COSINE", #cosine 距离适合文本向量
        params={"M": 16, "efConstruction": 200}, # M 控制索引复杂度，efConstruction 控制构建质量
    )
    client.create_index(
        collection_name=COLLECTION_NAME,
        index_params=index_params,
    )
    print(f"[OK] 已创建 Collection: {COLLECTION_NAME}")
    print(f"     Schema: id(INT64), text(VARCHAR), vector(FLOAT_VECTOR {VECTOR_DIM}D), source(VARCHAR)")
    print(f"     索引: HNSW (M=16, efConstruction=200), 度量: COSINE")


# ========== 3. 插入数据 ==========
def insert_data(client: MilvusClient) -> TextEmbedding:
    """将文本向量化后插入 Milvus"""
    # 准备测试文档
    documents = [
        "RAG（检索增强生成）通过检索外部知识库来增强大模型的回答能力，减少幻觉。",
        "HyDE（假设文档嵌入）让 LLM 先生成假设性回答，用回答的向量去检索，提升召回率。",
        "BM25 是经典的关键词检索算法，基于词频和逆文档频率计算相关性。",
        "Cross-Encoder 将 Query 和 Document 拼接后一起编码，精度高于 Bi-Encoder。",
        "Milvus 是生产级向量数据库，支持十亿级向量存储和分布式部署。",
        "FAISS 是 Facebook 开源的向量检索库，适合本地实验和中小规模场景。",
        "LangChain 是 LLM 应用开发框架，提供组件化的 RAG 构建能力。",
        "向量数据库选型：FAISS 适合本地实验，Milvus 适合生产环境，Chroma 适合轻量原型。",
    ]
    sources = ["rag_doc"] * 4 + ["tech_doc"] * 4  
    # [
    # "rag_doc", "rag_doc", "rag_doc", "rag_doc",
    # "tech_doc", "tech_doc", "tech_doc", "tech_doc"
    # ]

    # 加载本地 Embedding 模型
    print("[INFO] 正在加载 Embedding 模型...")
    embedding_model = TextEmbedding(EMBEDDING_MODEL)
    vectors = list(embedding_model.embed(documents))
    vectors = [list(v) for v in vectors]

    # 构造插入数据（MilvusClient 用 dict 列表）
    data = [
        {"text": doc, "vector": vec, "source": src}
        for doc, vec, src in zip(documents, vectors, sources)
    ]

    # 插入
    result = client.insert(collection_name=COLLECTION_NAME, data=data)
    print(f"[OK] 已插入 {result['insert_count']} 条数据")

    return embedding_model


# ========== 4. 向量搜索 ==========
def search_demo(client: MilvusClient, embedding_model: TextEmbedding):
    """演示向量相似度搜索（Top-K）"""
    query = "什么是 RAG 技术？"
    query_vector = list(list(embedding_model.embed([query]))[0])
    #.embed 返回二维数组，取第一行并转成 list 
    #embedding_model.embed([query])
    #返回 [[vector]]，需要取第一行 [0]，再转成 list


    # 搜索前必须加载 Collection 到内存
    client.load_collection(COLLECTION_NAME)

    # 搜索
    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[query_vector],
        limit=3,
        output_fields=["text", "source"],  # 指定返回文本和来源字段
        search_params={"metric_type": "COSINE"}, #指定使用余弦相似度进行搜索
    )

    print(f"\n{'=' * 60}")
    print(f"查询: {query}")
    print(f"{'=' * 60}")
    for i, hit in enumerate(results[0]):
        print(f"  [{i + 1}] 相似度: {hit['distance']:.4f}")
        print(f"      文本: {hit['entity']['text']}")
        print(f"      来源: {hit['entity']['source']}")


# ========== 5. 带过滤条件的搜索 ==========
def filtered_search_demo(client: MilvusClient, embedding_model: TextEmbedding):
    """演示标量过滤 + 向量搜索（混合检索的雏形）"""
    query = "向量数据库怎么选？"
    query_vector = list(list(embedding_model.embed([query]))[0])

    # 只搜索 source="tech_doc" 的文档
    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[query_vector],
        limit=3,
        output_fields=["text", "source"],
        filter='source == "tech_doc"',  # 标量过滤表达式
        search_params={"metric_type": "COSINE"},
    )

    print(f"\n{'=' * 60}")
    print(f"查询: {query}（过滤: source=tech_doc）")
    print(f"{'=' * 60}")
    for i, hit in enumerate(results[0]):
        print(f"  [{i + 1}] 相似度: {hit['distance']:.4f}")
        print(f"      文本: {hit['entity']['text']}")
        print(f"      来源: {hit['entity']['source']}")


# ========== 6. 删除数据 ==========
def delete_demo(client: MilvusClient):
    """演示按条件删除数据"""
    # 删除 source="rag_doc" 的数据
    result = client.delete(
        collection_name=COLLECTION_NAME,
        filter='source == "rag_doc"',
    )
    print(f"\n[OK] 已删除 source=rag_doc 的数据，删除 {result['delete_count']} 条")

    # 验证：查询剩余数据
    count = client.query(
        collection_name=COLLECTION_NAME,
        filter="",  # 空过滤 = 全部
        output_fields=["count(*)"],
    )
    print(f"     剩余数据: {count[0]['count(*)']} 条")


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        client = connect_milvus()
        create_collection(client)
        embedding_model = insert_data(client)
        search_demo(client, embedding_model)
        filtered_search_demo(client, embedding_model)
        delete_demo(client)
        print(f"\n[OK] Milvus 基础操作演示完成！")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("[INFO] 请确保 Milvus 服务已启动（docker compose up -d）")
