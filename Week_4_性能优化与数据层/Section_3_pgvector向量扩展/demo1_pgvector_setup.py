"""
demo1_pgvector_setup.py — pgvector 扩展安装与向量基础操作

学习目标：
1. 在 PostgreSQL 中启用 pgvector 扩展
2. 创建向量表（vector(384) 类型列）
3. 插入向量 + 执行相似度查询（L2 / Cosine / Inner Product）
4. 理解三种距离算子的语义差异

运行：python demo1_pgvector_setup.py
前置：PostgreSQL 已启动，密码 123456；pip install pgvector sqlalchemy psycopg2-binary fastembed numpy
"""

import logging
import numpy as np
from sqlalchemy import create_engine, text, Column, Integer, String
from sqlalchemy.orm import Session, DeclarativeBase
from pgvector.sqlalchemy import Vector  # pgvector 专用向量列类型

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql://postgres:123456@localhost:5433/postgres"


# ──────────────────────────────────────────────
# Step 1：连接数据库 & 启用 pgvector 扩展
# ──────────────────────────────────────────────
def setup_pgvector():
    """CREATE EXTENSION 需要超级用户权限，PostgreSQL 默认 postgres 用户即可"""
    engine = create_engine(DB_URL, echo=False) #echo=True 可打印 SQL
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))  # CREATE EXTENSION 不能在事务内执行
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("✅ pgvector 扩展已启用")
        except Exception as e:
            logger.error(f"❌ 启用 pgvector 失败：{e}")
            raise
    return engine


# ──────────────────────────────────────────────
# Step 2：定义 ORM 模型（向量表）
# ──────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


class Document(Base):
    """
    文档向量表
    embedding 列类型为 Vector(384) — 384 是 BGE-small 模型的维度
    【pgvector Vector(N)】N 建表时固定，后续无法修改
    """
    __tablename__ = "pgvector_docs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String(500), nullable=False, comment="文档内容")
    embedding = Column(Vector(512), nullable=False, comment="BGE-small-zh-v1.5 512维向量")

    def __repr__(self): #原理：定义对象的字符串表示形式，用于调试和日志输出
        return f"<Document id={self.id} content={self.content[:30]}...>"


# ──────────────────────────────────────────────
# Step 3：生成 Embedding（用 fastembed 本地模型）
# ──────────────────────────────────────────────
def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    用 BGE-small 模型将文本转为 384 维向量
    fastembed 自动下载模型到 models/ 目录
    """
    from fastembed import TextEmbedding
    # BGE-small：轻量、中文友好、384维
    model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    embeddings = list(model.embed(texts)) #type(embeddings) = list[numpy.ndarray]
    # fastembed 返回 numpy array，转 list 才能存入 pgvector
    return [emb.tolist() for emb in embeddings]


# ──────────────────────────────────────────────
# Step 4：插入数据
# ──────────────────────────────────────────────
def insert_documents(engine):
    """插入示例文档 + 向量"""
    texts = [
        "PostgreSQL 是一个功能强大的开源关系型数据库",
        "pgvector 扩展让 PostgreSQL 支持向量相似度搜索",
        "Redis 常用于缓存和会话存储，速度非常快",
        "Docker 可以打包应用及其依赖，实现环境一致性",
        "FastAPI 是一个高性能的 Python Web 框架，支持异步",
    ]

    logger.info("正在生成 Embedding（首次运行会下载模型）...")
    embeddings = get_embeddings(texts) #list[list[float]]

    Base.metadata.create_all(engine)  # 自动建表

    with Session(engine) as session:
        for text, emb in zip(texts, embeddings):
            doc = Document(content=text, embedding=emb)
            session.add(doc)
        session.commit()
        logger.info(f"✅ 已插入 {len(texts)} 条文档")


# ──────────────────────────────────────────────
# Step 5：相似度查询（三种距离算子）
# ──────────────────────────────────────────────
def similarity_search(engine):
    """用查询文本检索最相似的文档"""
    query_text = "向量数据库和相似度搜索"
    query_emb = get_embeddings([query_text])[0]

    with Session(engine) as session:
        # ── 距离算子说明 ──
        # 【<=>】Cosine Distance：余弦距离，[0, 2]，越小越相似（语义方向）
        # 【<->】L2 Distance：欧几里得距离，[0, ∞)，越小越相似（绝对位置）
        # 【<#>】Inner Product：负内积，(-∞, ∞)，越小越相似（等价于 -相似度）
        # 通常推荐 cosine 用于语义搜索
        logger.info(f"\n🔍 查询：「{query_text}」\n")

        for distance_op, label in [
            ("<=>", "余弦距离 (Cosine)"),
            ("<->", "欧氏距离 (L2)"),
            ("<#>", "负内积 (Inner Product)"),
        ]:
            # pgvector 支持在 ORDER BY 中直接使用距离算子
            stmt = text(f"""
                SELECT id, content, embedding {distance_op} :query_emb AS distance
                FROM pgvector_docs
                ORDER BY embedding {distance_op} :query_emb
                LIMIT 3
            """)
            results = session.execute(
                stmt,
                {"query_emb": str(query_emb)}  # pgvector 接受字符串形式的向量
            ).fetchall()  # fetchall() 返回所有结果行

            print(f"\n── {label} ──")
            for row in results:
                print(f"  [id={row[0]}] distance={row[2]:.4f} | {row[1]}")


# ──────────────────────────────────────────────
# Step 6：索引基础 — 精确搜索 vs 近似搜索
# ──────────────────────────────────────────────
def exact_vs_approx_search(engine):
    """
    演示「精确搜索」（全表扫描）vs 加索引后的「近似搜索」
    精确搜索适合 <10万 行，近似搜索适合百万级+
    """
    query_text = "Python Web 框架"
    query_emb = get_embeddings([query_text])[0]

    with Session(engine) as session:
        # 精确搜索：不加索引，逐行计算距离
        logger.info("\n📊 精确搜索（全表扫描）— EXPLAIN ANALYZE：")
        stmt = text("""
            EXPLAIN ANALYZE
            SELECT id, content, embedding <=> :query_emb AS distance
            FROM pgvector_docs
            ORDER BY embedding <=> :query_emb
            LIMIT 3
        """)
        plan = session.execute(stmt, {"query_emb": str(query_emb)}).fetchall()
        for line in plan:
            print(f"  {line[0]}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("pgvector 基础操作演示")
    logger.info("=" * 60)

    try:
        engine = setup_pgvector()
        insert_documents(engine)
        similarity_search(engine)
        exact_vs_approx_search(engine)
        logger.info("\n✅ 所有演示完成！")
    except Exception as e:
        logger.error(f"❌ 运行失败：{e}")
        raise
