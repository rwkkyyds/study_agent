"""
demo4_pgvector_rag.py — pgvector 端到端 RAG 系统

学习目标：
1. 完整 RAG 链路：文档加载 → 分块 → Embedding → pgvector 存储 → 检索 → LLM 生成
2. 手写递归分块器（零外部依赖，避免 torch DLL 问题）
3. 对比 pgvector RAG vs Chroma RAG 的优劣势

运行：python demo4_pgvector_rag.py
前置：PostgreSQL + pgvector 已就绪；pip install pgvector sqlalchemy psycopg2-binary fastembed openai
"""

import logging
import os
from sqlalchemy import create_engine, text, Column, Integer, String
from sqlalchemy.orm import Session, DeclarativeBase
from pgvector.sqlalchemy import Vector

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DB_URL = os.getenv("PGVECTOR_DATABASE_URL", "postgresql://postgres:123456@localhost:5433/postgres")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
EMBEDDING_DIM = 512


# ══════════════════════════════════════════════
# 数据库层
# ══════════════════════════════════════════════
class Base(DeclarativeBase):
    pass


class RAGDoc(Base):
    """RAG 文档表 — 存储分块后的文本+向量"""
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_text = Column(String(2000), nullable=False)
    source = Column(String(200), comment="来源标识")
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)


# ══════════════════════════════════════════════
# Step 1：文档加载与分块（零 torch 依赖）
# ══════════════════════════════════════════════

def recursive_split(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """
    递归字符分割器 — 等价于 LangChain 的 RecursiveCharacterTextSplitter
    按优先级尝试切割：双换行 → 单换行 → 句号 → 空格 → 字符
    【零外部依赖】避免 torch/langechain 在 Windows 上的 DLL 问题
    """
    separators = ["\n\n", "\n", "。", " ", ""]

    def _split(text: str, seps: list[str]) -> list[str]:
        """递归分割：当前分隔符切不动就换下一个"""
        sep = seps[0]
        next_seps = seps[1:]

        if not sep:  # 兜底：按字符硬切
            result = []
            for i in range(0, len(text), chunk_size - chunk_overlap):
                chunk = text[i:i + chunk_size]
                if chunk:
                    result.append(chunk)
            return result

        parts = text.split(sep)
        chunks = []
        for part in parts:
            if len(part) <= chunk_size:
                if part:
                    chunks.append(part)
            elif next_seps:
                chunks.extend(_split(part, next_seps))
            else:
                # 兜底硬切
                for i in range(0, len(part), chunk_size - chunk_overlap):
                    sub = part[i:i + chunk_size]
                    if sub:
                        chunks.append(sub)

        # 合并小块 + 添加上下文重叠
        merged = [chunks[0]] if chunks else []
        for chunk in chunks[1:]:
            prev = merged[-1]
            if len(prev) + len(chunk) <= chunk_size:
                merged[-1] = prev + chunk  # 合并
            else:
                # 从上一块的末尾取 overlap 字符拼到当前块开头
                if chunk_overlap > 0 and len(prev) > chunk_overlap:
                    chunk = prev[-chunk_overlap:] + chunk
                merged.append(chunk)
        return merged

    return [c.strip() for c in _split(text.strip(), separators) if c.strip()] #type: list[str]
def load_and_split_documents() -> list[dict]:
    """
    模拟加载文档 → 文本分块
    实际项目中会用 Unstructured / PyMuPDF 等加载 PDF
    """
    raw_doc = """
    PostgreSQL (简称 PG) 是一个功能强大的开源关系型数据库管理系统。
    它支持 ACID 事务、复杂查询、外键、触发器、视图等高级特性。
    自 1996 年发布以来，PG 以其稳定性、可扩展性和标准兼容性获得广泛认可。

    pgvector 是 PostgreSQL 的一个扩展，允许在数据库中存储和检索向量（embedding）。
    向量是 AI 模型生成的浮点数数组，用于表示文本、图像等非结构化数据的语义。
    通过 pgvector，开发者可以在同一条 SQL 中混合使用向量检索和传统过滤条件。

    HNSW (Hierarchical Navigable Small World) 是 pgvector 支持的高效近似最近邻索引。
    它通过构建多层图结构实现快速检索，查询时间随数据量增长呈对数级增长。
    相比 IVFFlat 索引，HNSW 在查询精度和速度上都有优势，但构建时间和内存占用更大。

    RAG (Retrieval-Augmented Generation) 是一种结合检索和生成的技术架构。
    首先通过 Embedding 模型将用户查询转为向量，然后在知识库中检索最相关的文档片段，
    最后将这些片段作为上下文注入 LLM 的 prompt 中，生成更准确、有据可依的回答。

    混合检索结合了全文检索（关键词匹配）和向量检索（语义理解）的优势。
    通过 RRF (Reciprocal Rank Fusion) 或其他融合算法综合排序，得到比单一检索更好的结果。
    """

    # 手写递归分块（零外部依赖，替代 langchain_text_splitters 避免 torch DLL 问题）
    chunks = recursive_split(raw_doc, chunk_size=500, chunk_overlap=50)

    logger.info(f"文档已分 {len(chunks)} 块（chunk_size=500, overlap=50）")
    return [{"text": c.strip(), "source": "postgresql_guide"} for c in chunks if c.strip()]


# ══════════════════════════════════════════════
# Step 2：Embedding + 存入 pgvector
# ══════════════════════════════════════════════
def embed_and_store(engine, chunks: list[dict]):
    """生成 embedding 并批量写入 pgvector"""
    from fastembed import TextEmbedding

    logger.info("正在生成 Embedding...")
    model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    texts = [c["text"] for c in chunks]
    embeddings = [e.tolist() for e in model.embed(texts)]

    # 重建表
    Base.metadata.drop_all(engine, tables=[RAGDoc.__table__], checkfirst=True)
    Base.metadata.create_all(engine)

    # 建 HNSW 索引
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_hnsw
            ON rag_documents USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))

    with Session(engine) as session:
        for chunk, emb in zip(chunks, embeddings):
            session.add(RAGDoc(
                chunk_text=chunk["text"],
                source=chunk["source"],
                embedding=emb
            ))
        session.commit()
        logger.info(f"✅ {len(chunks)} 个文档块已存入 pgvector")


# ══════════════════════════════════════════════
# Step 3：检索 — 取出 Top-K 最相关文档
# ══════════════════════════════════════════════
def retrieve(engine, query: str, top_k: int = 3) -> list[str]:
    """向量相似度检索，返回最相关的文档片段"""
    from fastembed import TextEmbedding
    model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    query_emb = list(model.embed([query]))[0].tolist()

    with Session(engine) as session:
        stmt = text("""
            SELECT chunk_text,
                   1 - (embedding <=> :q) AS similarity
            FROM rag_documents
            ORDER BY embedding <=> :q
            LIMIT :k
        """)
        rows = session.execute(stmt, {"q": str(query_emb), "k": top_k}).fetchall()
        logger.info(f"检索到 {len(rows)} 个相关片段")
        return [f"[相似度:{r[1]:.4f}] {r[0]}" for r in rows]


# ══════════════════════════════════════════════
# Step 4：LLM 生成回答
# ══════════════════════════════════════════════
def generate_answer(query: str, contexts: list[str]) -> str:
    """
    将检索到的上下文注入 Prompt，调用 DeepSeek 生成答案。
    RAG 核心价值：LLM 基于「外部知识」回答，而非依赖训练记忆。
    """
    from openai import OpenAI

    context_text = "\n\n---\n\n".join(contexts)
    system_prompt = (
        "你是一个知识助手。请仅根据以下提供的文档内容回答问题。"
        "如果文档中没有相关信息，请如实说「未找到相关信息」。"
        "\n\n【参考文档】\n"
        f"{context_text}"
    )

    client = OpenAI(
        api_key=DEEPSEEK_KEY,
        base_url="https://api.deepseek.com",
    )

    logger.info("正在调用 DeepSeek 生成回答...")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        temperature=0.3,
        max_tokens=500,
    )
    return response.choices[0].message.content


# ══════════════════════════════════════════════
# Step 5：完整 RAG 流程
# ══════════════════════════════════════════════
def rag_pipeline(engine, query: str):
    """RAG 全链路：检索 → 增强 → 生成"""
    logger.info(f'\n{"=" * 60}')
    logger.info(f'❓ 用户问题：「{query}」')
    logger.info(f'{"=" * 60}')

    # 检索
    contexts = retrieve(engine, query, top_k=3)
    print("\n📚 检索到的上下文片段：")
    for i, ctx in enumerate(contexts, 1):
        print(f"  [{i}] {ctx[:120]}...")

    # 生成
    answer = generate_answer(query, contexts)
    print(f"\n🤖 AI 回答：\n  {answer}")


# ══════════════════════════════════════════════
# Step 6：pgvector RAG vs 传统向量库对比
# ══════════════════════════════════════════════
def show_comparison():
    print("""
╔══════════════════╦═══════════════════╦═════════════════════╗
║      维度         ║   pgvector        ║  FAISS / Chroma     ║
╠══════════════════╬═══════════════════╬═════════════════════╣
║ 部署复杂度        ║ 低（PG自带）      ║ 中（额外服务/库）    ║
║ 数据一致性        ║ 强（ACID事务）    ║ 弱（无事务保证）     ║
║ 混合检索          ║ 原生支持          ║ 需自行拼接           ║
║ 元数据过滤        ║ SQL WHERE 原生    ║ 有限或需额外配置     ║
║ 分布式扩展        ║ 读副本/分区       ║ 分片方案成熟         ║
║ 向量检索性能      ║ 中等（HNSW）      ║ 更快（C++优化）      ║
║ 适合场景          ║ 已有PG的项目      ║ 独立向量检索场景     ║
╚══════════════════╩═══════════════════╩═════════════════════╝

💡 选型建议：
  如果项目已用 PostgreSQL → 直接用 pgvector，减少架构复杂度
  如果纯向量检索且数据量极大 → 考虑 Milvus
  如果快速原型验证 → FAISS/Chroma 更轻量
    """)


# ══════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("pgvector 端到端 RAG 系统")
    logger.info("=" * 60)

    try:
        engine = create_engine(DB_URL, echo=False)

        # 1. 加载文档 + 生成向量 + 存储
        chunks = load_and_split_documents()
        embed_and_store(engine, chunks)

        # 2. RAG 问答测试
        for query in [
            "什么是 HNSW 索引？它有什么优缺点？",
            "RAG 架构的核心流程是什么？",
            "混合检索和单一检索哪个更好？",
        ]:
            rag_pipeline(engine, query)

        # 3. 对比总结
        show_comparison()
        logger.info("\n✅ pgvector RAG 演示完成！")
    except Exception as e:
        logger.error(f"❌ 运行失败：{e}")
        raise
