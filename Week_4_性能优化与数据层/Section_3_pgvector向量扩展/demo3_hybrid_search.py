"""
demo3_hybrid_search.py — PostgreSQL 混合检索：全文检索 + 向量检索 + RRF 融合

学习目标：
1. 用 PostgreSQL tsvector/tsquery 实现 BM25 级别全文检索
2. 将全文检索结果与向量检索结果通过 RRF 融合排序
3. 理解混合检索为什么优于单一检索方式

运行：python demo3_hybrid_search.py
前置：已执行 demo1_pgvector_setup.py 建表（本文件会重建表结构）
"""

import logging
import numpy as np
from sqlalchemy import create_engine, text, Column, Integer, String, Float
from sqlalchemy.orm import Session, DeclarativeBase
from pgvector.sqlalchemy import Vector

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql://postgres:123456@localhost:5433/postgres"


# ──────────────────────────────────────────────
# Step 1：定义支持全文检索 + 向量的混合表
# ──────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


class Article(Base):
    """
    混合检索表：同时支持全文检索（tsvector）和向量检索（vector）
    【GENERATED ALWAYS AS】search_vec 自动从 content 生成，无需手动维护
    """
    __tablename__ = "hybrid_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(String(2000), nullable=False)  
    # tsvector 全文检索列 — 从 title+content 自动生成 
    search_vec = Column(
        String,
        nullable=False,
        comment="tsvector 全文检索向量，自动从 title+content 生成"
    )
    # pgvector 向量列
    embedding = Column(Vector(512), nullable=False)


# ──────────────────────────────────────────────
# Step 2：建表（含 GIN 索引 + 向量索引）
# ──────────────────────────────────────────────
def setup_hybrid_table(engine):
    """重建表并创建双索引"""
    Base.metadata.drop_all(engine, tables=[Article.__table__], checkfirst=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # GIN 索引：加速全文检索
        # 【GIN】Generalized Inverted Index，适合 tsvector/JSONB/数组 等复合类型
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_articles_fts
            ON hybrid_articles USING GIN (to_tsvector('simple', search_vec))
        """))
        # HNSW 向量索引
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_articles_vec
            ON hybrid_articles USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))
        session.commit()
        logger.info("✅ 混合表 + GIN + HNSW 索引已就绪")


# ──────────────────────────────────────────────
# Step 3：插入测试数据
# ──────────────────────────────────────────────
def insert_articles(engine):
    """插入包含标题+正文的文档"""
    from fastembed import TextEmbedding

    articles = [
        ("Python 异步编程入门", "Python 的 asyncio 库提供了协程和事件循环，用于编写高并发程序"),
        ("PostgreSQL 性能优化", "使用 EXPLAIN ANALYZE 分析查询计划，合理创建索引提升性能"),
        ("Redis 缓存策略", "Redis 支持多种数据结构，常用于缓存热点数据、会话存储和限流"),
        ("Docker 容器化部署", "Docker 让应用打包为镜像，通过 Compose 编排多服务"),
        ("向量数据库对比", "pgvector 让 PostgreSQL 支持向量检索，与 Milvus 和 FAISS 各有所长"),
        ("全文检索技术", "PostgreSQL 内置 tsvector 全文检索，支持中文分词和相关性排序"),
        ("LangChain Agent 开发", "LangGraph 的 StateGraph 可以构建复杂的 Agent 推理工作流"),
        ("机器学习模型部署", "将训练好的模型封装为 API，通过 Docker 实现可复现部署"),
    ]

    model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    logger.info("生成 Embedding...")
    contents = [f"{a[0]} {a[1]}" for a in articles]
    embeddings = [e.tolist() for e in model.embed(contents)]

    with Session(engine) as session:
        for (title, content), emb in zip(articles, embeddings):
            article = Article(
                title=title,
                content=content,
                search_vec=f"{title} {content}",  # tsvector 源文本
                embedding=emb
            )
            session.add(article)
        session.commit()
        logger.info(f"✅ 已插入 {len(articles)} 篇文章")


# ──────────────────────────────────────────────
# Step 4：全文检索
# ──────────────────────────────────────────────
def fulltext_search(engine, query: str) -> list[dict]:
    """
    PostgreSQL 全文检索：
    【plainto_tsquery】将自然语言转为 tsquery（自动去除停用词、分词）
    【ts_rank】BM25 风格的相关性评分
    """
    with Session(engine) as session:
        stmt = text("""
            SELECT id, title, content,
                   ts_rank(to_tsvector('simple', search_vec),
                           plainto_tsquery('simple', :query)) AS rank
            FROM hybrid_articles
            WHERE to_tsvector('simple', search_vec) @@ plainto_tsquery('simple', :query)
            ORDER BY rank DESC
            LIMIT 5
        """) #对 hybrid_articles 表做简单分词模式全文检索，
        #匹配传入关键词 :query，按匹配相关度降序取前 5 条
        rows = session.execute(stmt, {"query": query}).fetchall()
        return [{"id": r[0], "title": r[1], "content": r[2], "score": float(r[3])} for r in rows]


# ──────────────────────────────────────────────
# Step 5：向量检索
# ──────────────────────────────────────────────
def vector_search(engine, query: str) -> list[dict]:
    """余弦相似度向量检索"""
    from fastembed import TextEmbedding
    model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    query_emb = list(model.embed([query]))[0].tolist()

    with Session(engine) as session:
        stmt = text("""
            SELECT id, title, content,
                   1 - (embedding <=> :q) AS similarity
            FROM hybrid_articles
            ORDER BY embedding <=> :q
            LIMIT 5
        """)
        rows = session.execute(stmt, {"q": str(query_emb)}).fetchall()
        return [{"id": r[0], "title": r[1], "content": r[2],
                 "score": round(float(r[3]), 4)} for r in rows]


# ──────────────────────────────────────────────
# Step 6：RRF 融合（混合检索核心）
# ──────────────────────────────────────────────
def rrf_fusion(fts_results: list[dict], vec_results: list[dict], k: int = 60) -> list[dict]:
    """
    【RRF】Reciprocal Rank Fusion — 倒数排名融合
    公式：RRF(d) = Σ 1/(k + rank_i(d))
    - k 是平滑常数（默认 60），防止单个排名为 0 导致分数爆炸
    - 不依赖原始分数的量纲，只需排名，适合异构检索源融合

    流程：
    1. 对每个文档，计算它在全文检索中的排名 rank_fts
    2. 对每个文档，计算它在向量检索中的排名 rank_vec
    3. 融合分 = 1/(k+rank_fts) + 1/(k+rank_vec)
    4. 按融合分降序排列
    """
    scores = {}

    # 全文检索排名贡献
    for rank, item in enumerate(fts_results, start=1):
        doc_id = item["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)

    # 向量检索排名贡献
    for rank, item in enumerate(vec_results, start=1):
        doc_id = item["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)

    # 按融合分排序
    all_items = {item["id"]: item for item in fts_results + vec_results}
    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return [{
        **all_items[doc_id],
        "rrf_score": round(score, 4)
    } for doc_id, score in fused]


# ──────────────────────────────────────────────
# Step 7：对比展示
# ──────────────────────────────────────────────
def compare_search(engine, query: str):
    """对比三种检索方式的结果"""
    logger.info(f'\n{"=" * 60}')
    logger.info(f'🔍 查询：「{query}」')
    logger.info(f'{"=" * 60}')

    fts = fulltext_search(engine, query)
    vec = vector_search(engine, query)
    fused = rrf_fusion(fts, vec)

    # 全文检索结果
    print(f"\n── 全文检索 (ts_rank) ──")
    for r in fts:
        print(f"  [{r['title']}] score={r['score']:.4f}")

    # 向量检索结果
    print(f"\n── 向量检索 (Cosine) ──")
    for r in vec:
        print(f"  [{r['title']}] similarity={r['score']:.4f}")

    # 混合检索结果
    print(f"\n── 混合检索 (RRF 融合) ──")
    for r in fused:
        print(f"  [{r['title']}] rrf_score={r['rrf_score']:.4f}")

    print("\n💡 对比分析：")
    print("  全文检索 → 精确匹配关键词（如 '数据库'）")
    print("  向量检索 → 理解语义相似度（如 '数据存储' ≈ '数据库'）")
    print("  混合检索 → 融合两者优势，召回率和准确率双高")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("混合检索：全文 + 向量 + RRF 融合")
    logger.info("=" * 60)

    try:
        engine = create_engine(DB_URL, echo=False)
        setup_hybrid_table(engine)
        insert_articles(engine)

        # 多个查询对比
        for q in [
            "数据库性能优化方法",
            "Python 异步编程",
            "部署和容器化",
        ]:
            compare_search(engine, q)

        logger.info("\n✅ 混合检索演示完成！")
    except Exception as e:
        logger.error(f"❌ 运行失败：{e}")
        raise
