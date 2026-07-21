"""
demo2_vector_index.py — IVFFlat vs HNSW 向量索引对比

学习目标：
1. 理解 IVFFlat（倒排+量化）和 HNSW（分层可导航小世界图）的原理差异
2. 掌握索引创建语法与参数调优（lists / m / ef_construction）
3. 用 EXPLAIN ANALYZE 对比索引前后的查询性能

运行：python demo2_vector_index.py
前置：已执行 demo1_pgvector_setup.py 建表并插入数据
"""

import logging
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql://postgres:123456@localhost:5433/postgres"


# ──────────────────────────────────────────────
# Step 1：生成批量测试数据
# ──────────────────────────────────────────────
def generate_test_data(engine, count: int = 5000):
    """
    插入 N 条随机向量数据，用于对比索引性能。
    【数据量太少时索引优势不明显】生产环境至少 1 万条才建议建索引。
    """
    from fastembed import TextEmbedding
    import random

    logger.info(f"正在生成 {count} 条测试数据...")
    model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")

    # 模板文本 + 随机后缀，生成不同语义的向量
    templates = [
        "数据库性能优化技巧",
        "Python 异步编程指南",
        "Redis 缓存策略实践",
        "Docker 容器编排入门",
        "机器学习模型部署方案",
        "微服务架构设计模式",
        "前端 React 组件设计",
        "网络安全防护基础",
        "消息队列 RabbitMQ 实战",
        "API 网关限流策略",
    ]

    with Session(engine) as session:
        batch = []
        for i in range(count):
            tpl = random.choice(templates)
            content = f"{tpl} - 变体 {i:05d}"
            batch.append(content)
            # 每 100 条批量提交一次
            if len(batch) >= 100:
                embeddings = list(model.embed(batch))
                for txt, emb in zip(batch, embeddings):
                    session.execute(
                        text("INSERT INTO pgvector_docs (content, embedding) VALUES (:c, :e)"),
                        {"c": txt, "e": str(emb.tolist())}
                    )
                session.commit()
                batch = []
        # 剩余数据
        if batch:
            embeddings = list(model.embed(batch))
            for txt, emb in zip(batch, embeddings):
                session.execute(
                    text("INSERT INTO pgvector_docs (content, embedding) VALUES (:c, :e)"),
                    {"c": txt, "e": str(emb.tolist())}
                )
            session.commit()

    logger.info(f"✅ 已插入 {count} 条测试数据")


# ──────────────────────────────────────────────
# Step 2：无索引时的查询性能（基准线）
# ──────────────────────────────────────────────
def baseline_search(engine):
    """全表扫描 — 作为性能基准"""
    query_emb = np.random.rand(512).tolist()  #这里随机生成一个 512 维向量作为查询向量

    with Session(engine) as session:
        logger.info("\n📊 无索引（全表扫描 Sequential Scan）:")
        stmt = text("""
            EXPLAIN ANALYZE
            SELECT id, content, embedding <=> :q AS dist
            FROM pgvector_docs
            ORDER BY embedding <=> :q
            LIMIT 10
        """)
        result = session.execute(stmt, {"q": str(query_emb)}).fetchall() 
        for line in result:
            print(f"  {line[0]}")


# ──────────────────────────────────────────────
# Step 3：IVFFlat 索引
# ──────────────────────────────────────────────
def demo_ivfflat(engine):
    """
    【IVFFlat】倒排文件平坦索引 (Inverted File Flat)
    - 原理：用 K-Means 将向量聚类为 N 个桶（lists），查询时只搜最近的几个桶
    - lists 参数：聚类中心数，建议 rows/1000 到 rows/100
    - 特点：构建快、内存省，但精度不如 HNSW
    - 适用：中等规模（10万~100万），对精度要求不极端的场景
    """
    with Session(engine) as session:
        # 先建索引
        logger.info("\n🔧 创建 IVFFlat 索引...")
        try:
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ivfflat
                ON pgvector_docs
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100) 
            """))
            session.commit()
            logger.info("✅ IVFFlat 索引创建成功 (lists=100)")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败：{e}")

        # 查询性能
        query_emb = np.random.rand(512).tolist()
        logger.info("\n📊 IVFFlat 索引查询性能：")
        stmt = text("""
            EXPLAIN ANALYZE
            SELECT id, content, embedding <=> :q AS dist
            FROM pgvector_docs
            ORDER BY embedding <=> :q
            LIMIT 10
        """) 
        result = session.execute(stmt, {"q": str(query_emb)}).fetchall()
        for line in result:
            print(f"  {line[0]}")

    # 删除索引，为 HNSW 演示腾空间
    with Session(engine) as session:
        session.execute(text("DROP INDEX IF EXISTS idx_ivfflat"))
        session.commit()


# ──────────────────────────────────────────────
# Step 4：HNSW 索引
# ──────────────────────────────────────────────
def demo_hnsw(engine):
    """
    【HNSW】分层可导航小世界图 (Hierarchical Navigable Small World)
    - 原理：构建多层图结构，高层稀疏（长距离跳转），底层密集（精确搜索）
    - m 参数：每层每个节点最多连 m 个邻居，默认 16（越大精度越高，内存越大）
    - ef_construction：构建时的搜索深度，默认 64（越大精度越高，构建越慢）
    - 特点：查询精度高、速度快，但内存占用大、构建慢
    - 适用：高精度场景（百万~亿级），生产环境首选
    """
    with Session(engine) as session:
        logger.info("\n🔧 创建 HNSW 索引...")
        try:
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_hnsw
                ON pgvector_docs
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))
            session.commit()
            logger.info("✅ HNSW 索引创建成功 (m=16, ef_construction=64)")
        except Exception as e:
            logger.warning(f"索引已存在或创建失败：{e}")

        query_emb = np.random.rand(512).tolist()
        logger.info("\n📊 HNSW 索引查询性能：")
        stmt = text("""
            EXPLAIN ANALYZE
            SELECT id, content, embedding <=> :q AS dist
            FROM pgvector_docs
            ORDER BY embedding <=> :q
            LIMIT 10
        """)
        result = session.execute(stmt, {"q": str(query_emb)}).fetchall()
        for line in result:
            print(f"  {line[0]}")


# ──────────────────────────────────────────────
# Step 5：索引选型总结
# ──────────────────────────────────────────────
def print_summary():
    print("""
╔═══════════╦══════════════════╦══════════════════╗
║   维度     ║     IVFFlat      ║      HNSW        ║
╠═══════════╬══════════════════╬══════════════════╣
║ 构建速度   ║ 快               ║ 慢               ║
║ 查询速度   ║ 较快             ║ 很快             ║
║ 查询精度   ║ 中（近似）        ║ 高（可调）        ║
║ 内存占用   ║ 低               ║ 高               ║
║ 数据规模   ║ 10万~100万       ║ 百万~亿级         ║
║ 生产推荐   ║ 次选             ║ 首选             ║
╚═══════════╩══════════════════╩══════════════════╝
    """)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("向量索引 IVFFlat vs HNSW 对比")
    logger.info("=" * 60)

    try:
        engine = create_engine(DB_URL, echo=False)

        # 检查数据量，不够则补充
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM pgvector_docs")
            ).scalar() #.scalar() 返回单个值
            logger.info(f"当前数据量：{count} 条")
            if count < 1000:
                generate_test_data(engine, count=5000)

        baseline_search(engine)
        demo_ivfflat(engine)
        demo_hnsw(engine)
        print_summary()
        logger.info("✅ 所有演示完成！")
    except Exception as e:
        logger.error(f"❌ 运行失败：{e}")
        raise
