"""
demo1_index_types.py - PostgreSQL 索引类型与优化策略

学习目标：
1. 理解 B-tree、GIN、GiST 索引的适用场景
2. 掌握复合索引、部分索引、覆盖索引的用法
3. 用 EXPLAIN ANALYZE 查看索引是否生效

运行：python demo1_index_types.py
前置：PostgreSQL 已启动，密码 123456
"""

import logging
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, Float, Index, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, DeclarativeBase
from datetime import datetime, timedelta
import random

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# PostgreSQL 连接
# ============================================================
DB_URL = "postgresql+psycopg2://postgres:123456@localhost:5432/postgres"
engine = create_engine(DB_URL, echo=False)


# ============================================================
# Model 定义
# ============================================================
class Base(DeclarativeBase): 
    pass


class Product(Base):
    """商品表 - 演示各种索引类型"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)        # 分类
    price = Column(Float, nullable=False)
    tags = Column(JSONB, default=list)                     # 标签（JSONB）
    description = Column(String(1000), default="")
    is_active = Column(Boolean, default=True)  #Column 是 字段
    stock = Column(Integer, default=0)  # 库存
    created_at = Column(DateTime, default=datetime.now) 

    # ---- 各种索引定义 ----
    __table_args__ = (
        # 1. B-tree（默认）：等值/范围/排序
        Index("idx_product_category", "category"),  

        # 2. 复合索引：多列联合查询，高选择性列放前面
        Index("idx_product_cat_price", "category", "price"),

        # 3. 部分索引：只索引活跃商品，节省空间
        Index("idx_product_active_price", "price",
              postgresql_where=text("is_active = true")),

        # 4. 覆盖索引：INCLUDE 包含额外列，避免回表
        Index("idx_product_cat_cover", "category",
              postgresql_include=["name", "price", "stock"]),

        # 5. GIN 索引：JSONB 字段（PostgreSQL 特有，核心！）
        Index("idx_product_tags", "tags", postgresql_using="gin"),
    )


# ============================================================
# 工具函数
# ============================================================
def explain(session: Session, sql: str, label: str = ""):
    """执行 EXPLAIN ANALYZE，查看真实执行计划"""
    logger.info(f"\n{'='*60}")
    logger.info(f"EXPLAIN ANALYZE: {label}") #label 用于标记当前执行的 SQL 语句的描述
    logger.info(f"SQL: {sql.strip()[:120]}")
    logger.info("-"*60)
    result = session.execute(text(f"EXPLAIN ANALYZE {sql}"))  #text() 用于将 SQL 字符串转换为 SQLAlchemy 可识别的文本对象
    for row in result:
        logger.info(f"  {row[0]}")
    logger.info("="*60)


# ============================================================
# 数据初始化
# ============================================================
def init_data(session: Session, count: int = 100000):
    """插入测试数据"""
    logger.info(f"正在插入 {count} 条商品数据...")

    # 先删旧表
    session.execute(text("DROP TABLE IF EXISTS products CASCADE"))
    session.commit()

    # 重新建表
    Base.metadata.create_all(engine) #建所有继承Base的表

    categories = ["电子产品", "服装", "食品", "图书", "家居", "运动", "美妆", "母婴"]
    tag_pool = ["热销", "新品", "限时", "包邮", "好评", "推荐", "清仓", "预售"]

    batch = []
    for i in range(count):
        product = Product(
            name=f"商品_{i:06d}",  #:06d 表示数字前面补零，保证总长度为6位
            category=random.choice(categories),
            price=round(random.uniform(1, 9999), 2), # 价格，保留两位小数 round() 函数用于将浮点数四舍五入到指定的小数位数
            tags=random.sample(tag_pool, k=random.randint(1, 4)), # 随机选择1-4个标签,sample() 函数用于从列表中随机选择指定数量的元素
            description=f"这是商品{i}的描述" * random.randint(1, 3),
            is_active=random.random() < 0.8,  # 80% 活跃
            stock=random.randint(0, 1000),
            created_at=datetime.now() - timedelta(days=random.randint(0, 730)),
        )
        batch.append(product)
        if len(batch) >= 5000:
            session.add_all(batch)
            session.commit()
            batch = []

    if batch:
        session.add_all(batch)
        session.commit()

    # 更新统计信息（PostgreSQL 需要这个才能生成准确的执行计划）
    session.execute(text("ANALYZE products")) # text里面的参数是 SQL 语句 ANALYZE products 用于更新 products 表的统计信息，以便查询优化器能够生成更准确的执行计划
    session.commit()
    logger.info(f"数据插入完成，共 {count} 条")


# ============================================================
# 主程序
# ============================================================
def main():
    with Session(engine) as session:
        # 1. 初始化数据
        init_data(session, count=100000)

        # ============================================================
        # 2. 无索引 vs 有索引
        # ============================================================
        logger.info("\n" + "="*60)
        logger.info("【实验1】无索引 vs 有索引 查询对比")
        logger.info("="*60)

        # 先删掉 category 索引
        session.execute(text("DROP INDEX IF EXISTS idx_product_category"))
        session.commit()

        # 无索引：全表扫描 Seq Scan
        explain(session,
                "SELECT * FROM products WHERE category = '电子产品'",
                "无索引 - 全表扫描 Seq Scan")

        # 创建索引
        session.execute(text("CREATE INDEX idx_product_category ON products(category)"))
        session.commit()

        # 有索引：索引扫描 Index Scan
        explain(session,
                "SELECT * FROM products WHERE category = '电子产品'",
                "有索引 - 索引扫描 Index Scan")

        # ============================================================
        # 3. 复合索引 - 最左前缀原则
        # ============================================================
        logger.info("\n" + "="*60)
        logger.info("【实验2】复合索引 - 最左前缀原则")
        logger.info("="*60)

        # 命中前缀列 → 索引生效
        explain(session,
                "SELECT * FROM products WHERE category = '电子产品' AND price < 500",
                "查询 category+price → 完全命中复合索引")

        # 只查第一列 → 索引生效（最左前缀）
        explain(session,
                "SELECT * FROM products WHERE category = '电子产品'",
                "只查 category → 命中复合索引前缀")

        # 只查第二列 → 索引不生效！
        explain(session,
                "SELECT * FROM products WHERE price < 500",
                "只查 price → 无法命中复合索引（违反最左前缀）")

        # ============================================================
        # 4. 部分索引（Partial Index）
        # ============================================================
        logger.info("\n" + "="*60)
        logger.info("【实验3】部分索引 - 只索引活跃商品")
        logger.info("="*60)

        # 部分索引：只索引 is_active=true 的行（约 80%）
        # 条件必须匹配索引的 WHERE 子句才能生效
        explain(session,
                "SELECT * FROM products WHERE is_active = true AND price < 100",
                "查询活跃商品 → 命中部分索引")

        explain(session,
                "SELECT * FROM products WHERE price < 100",
                "查询所有商品（含下架）→ 部分索引不生效")

        # ============================================================
        # 5. 覆盖索引（Covering Index / INCLUDE）
        # ============================================================
        logger.info("\n" + "="*60)
        logger.info("【实验4】覆盖索引 - INCLUDE 避免回表")
        logger.info("="*60)

        # 覆盖索引：索引本身包含 name, price, stock
        # 查询只取这些列时 → Index Only Scan（最快）
        explain(session,
                "SELECT name, price, stock FROM products WHERE category = '电子产品'",
                "覆盖索引查询 → Index Only Scan（不用回表）")

        # 查询包含索引外的列 → 需要回表
        explain(session,
                "SELECT name, price, stock, description FROM products WHERE category = '电子产品'",
                "包含 description → 需要回表取数据")

        # ============================================================
        # 6.  GIN 索引 - JSONB 查询
        # ============================================================
        logger.info("\n" + "="*60)
        logger.info("【实验5】GIN 索引 - JSONB 字段查询")
        logger.info("="*60)

        # GIN 索引支持 JSONB 的 @> (包含) 操作符
        explain(session,
                """SELECT * FROM products
                   WHERE tags @> '["热销"]'::jsonb""",
                "GIN 索引查询 - tags 包含 '热销'")

        explain(session,
                """SELECT * FROM products
                   WHERE tags @>'["热销", "新品"]'::jsonb""",
                "GIN 索引查询 - tags 同时包含 '热销' 和 '新品'")

        # ============================================================
        # 7. 索引代价：写入性能对比
        # ============================================================
        logger.info("\n" + "="*60)
        logger.info("【实验6】索引的代价 - 写入变慢")
        logger.info("="*60)

        import time

        # 有索引时的写入
        start = time.perf_counter() #perf_counter() 用于获取高精度的时间戳，适合测量时间间隔
        for i in range(500):
            session.add(Product(
                name=f"测试商品_{i}", category="测试", price=99.0,
                tags=["测试"], is_active=True, stock=1
            ))
        session.commit()
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"有索引写入 500 条: {elapsed:.0f}ms")

        # 清理测试数据
        session.execute(text("DELETE FROM products WHERE category = '测试'"))
        session.commit()

        # ============================================================
        # 8. 清理
        # ============================================================
        logger.info("\n" + "="*60)
        logger.info("【清理】删除测试表")
        logger.info("="*60)
        session.execute(text("DROP TABLE IF EXISTS products CASCADE"))
        session.commit()
        logger.info("测试表已删除")

        # ============================================================
        # 9. 索引设计原则总结
        # ============================================================
        logger.info("\n" + "="*60)
        logger.info("【PostgreSQL 索引类型总结】")
        logger.info("="*60)
        logger.info("""
        ┌─────────────┬──────────────────────────────────────────────┐
        │ 索引类型     │ 适用场景                                      │
        ├─────────────┼──────────────────────────────────────────────┤
        │ B-tree      │ 等值(=)、范围(< >)、排序(ORDER BY)            │
        │ (默认)       │ → 绝大多数场景用这个就够了                     │
        ├─────────────┼──────────────────────────────────────────────┤
        │ GIN         │ JSONB @>、全文搜索 tsvector、数组 contains     │
        │             │ → PostgreSQL 独有优势，AI/RAG 场景必备         │
        ├─────────────┼──────────────────────────────────────────────┤
        │ GiST        │ 地理数据(PostGIS)、范围类型、相似度搜索        │
        │             │ → pgvector 的 ivfflat/hnsw 索引基于此         │
        ├─────────────┼──────────────────────────────────────────────┤
        │ BRIN        │ 大表按时间顺序存储（日志、时序数据）            │
        │             │ → 索引极小，适合超大表                         │
        ├─────────────┼──────────────────────────────────────────────┤
        │ 部分索引     │ 只索引满足 WHERE 条件的行                     │
        │             │ → 数据分布不均匀时节省空间                     │
        ├─────────────┼──────────────────────────────────────────────┤
        │ 覆盖索引     │ INCLUDE 额外列，避免回表                      │
        │             │ → 高频查询只取少量列时用                       │
        └─────────────┴──────────────────────────────────────────────┘

        索引的代价：
        → 占用存储（通常是表大小的 10%-30%）
        → 写入变慢（INSERT/UPDATE/DELETE 需维护索引）
        → 不要过度索引！只给高频查询加索引
        """)


if __name__ == "__main__":
    main()
