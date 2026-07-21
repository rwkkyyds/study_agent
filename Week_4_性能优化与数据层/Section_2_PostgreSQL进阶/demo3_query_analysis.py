"""
demo3_query_analysis.py - 查询性能分析与 N+1 问题

学习目标：
1. 用 EXPLAIN ANALYZE 分析查询计划
2. 理解 N+1 查询问题及其危害
3. 掌握 Eager Loading（joinedload/selectinload）解决 N+1
4. 学会识别慢查询并优化

运行：python demo3_query_analysis.py
前置：PostgreSQL 已启动，密码 123456
"""

import logging
import time
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    ForeignKey, text, event
)
from sqlalchemy.orm import (
    Session, DeclarativeBase, relationship,
    joinedload, selectinload, subqueryload
)

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ============================================================
# Model 定义：用户 + 订单（一对多关系）
# ============================================================
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)

    # 一对多：一个用户有多个订单
    orders = relationship("Order", back_populates="user", lazy="select")  # 默认 lazy loading


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)

    user = relationship("User", back_populates="orders")


# ============================================================
# 工具函数
# ============================================================
def timed(label: str):
    """计时装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.perf_counter() # time.perf_counter() 提供高精度计时，适合测量短时间间隔
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(f"⏱ [{label}] 耗时: {elapsed:.2f}ms")
            return result
        return wrapper
    return decorator


def count_queries(engine, func):
    """统计函数执行期间的 SQL 查询次数"""
    query_count = [0]

    @event.listens_for(engine, "before_cursor_execute") #before_cursor_execute 事件在每次 SQL 执行前触发
    def count(conn, cursor, statement, parameters, context, executemany):
        #conn = 数据库连接对象，cursor = 游标对象，statement = SQL 语句，
        # parameters = 参数，context = 上下文，executemany = 是否批量执行
        query_count[0] += 1

    result = func()

    # 移除监听
    event.remove(engine, "before_cursor_execute", count)

    return result, query_count[0]


# ============================================================
# 数据初始化
# ============================================================
def init_data(session: Session, engine):
    """创建测试数据：100 个用户，每个用户 10 个订单"""
    logger.info("正在创建测试数据...")
    session.execute(text("DROP TABLE IF EXISTS orders CASCADE"))
    session.execute(text("DROP TABLE IF EXISTS users CASCADE"))
    session.commit()
    Base.metadata.create_all(engine)

    for i in range(1, 101):
        user = User(name=f"user_{i}", email=f"user_{i}@test.com")
        session.add(user)
        session.flush()  # 获取 user.id

        for j in range(1, 11):
            order = Order(
                user_id=user.id,
                product=f"product_{j}",
                amount=round(100 + j * 10.5, 2)
            )
            session.add(order)

    session.commit()
    logger.info("数据创建完成：100 用户 × 10 订单 = 1100 条记录")


# ============================================================
# Part 1: N+1 问题演示
# ========================-====================================
def demo_n_plus_one(engine):
    """
    N+1 问题 = 查询 1 次主表 + N 次关联表

    场景：查出 100 个用户，然后遍历每个用户的订单
    → 1 次查 users + 100 次查 orders = 101 次 SQL 查询！
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 1】N+1 查询问题演示")
    logger.info("="*60)

    with Session(engine) as session:
        # ---- 演示 N+1 ----
        logger.info("\n--- N+1 问题（lazy loading）---")

        def n_plus_one_query():
            users = session.execute(
                text("SELECT id, name FROM users LIMIT 10")
            ).fetchall()
            result = []
            for user in users:
                # 每次访问 user.orders 都会触发一次 SQL 查询！
                orders = session.execute(
                    text(f"SELECT * FROM orders WHERE user_id = {user[0]}")
                ).fetchall()
                result.append((user[1], len(orders)))
            return result

        result, query_count = count_queries(engine, n_plus_one_query)
        logger.info(f"查询了 {len(result)} 个用户")
        logger.info(f"总共执行了 {query_count} 次 SQL 查询！")
        logger.info(f"（1 次查用户 + {len(result)} 次查订单 = {query_count} 次）")


# ============================================================
# Part 2: 用 JOIN 一次查询解决 N+1
# ============================================================
def demo_join_solution(engine):
    """用 SQL JOIN 一次性查出所有数据"""
    logger.info("\n" + "="*60)
    logger.info("【Part 2】用 JOIN 解决 N+1")
    logger.info("="*60)

    with Session(engine) as session:
        logger.info("\n--- JOIN 查询（1 次搞定）---")

        def join_query():
            result = session.execute(text("""
                SELECT u.name, COUNT(o.id) as order_count
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id
                GROUP BY u.id, u.name
                ORDER BY u.id
                LIMIT 10
            """)).fetchall()
            return result #返回 [(user_name, order_count), ...] 的列表

        result, query_count = count_queries(engine, join_query)
        logger.info(f"查询了 {len(result)} 个用户的订单统计")
        logger.info(f"总共执行了 {query_count} 次 SQL 查询")
        for row in result[:5]:
            logger.info(f"  {row[0]}: {row[1]} 个订单")


# ============================================================
# Part 3: SQLAlchemy Eager Loading
# ============================================================
def demo_eager_loading(engine):
    """
    Eager Loading = 预加载关联数据

    三种方式：
    1. joinedload  → 用 LEFT JOIN，一次查询（适合一对一、多对一）
    2. selectinload → 用 IN 子查询，两次查询（适合一对多）
    3. subqueryload → 用子查询（性能较差，不推荐）
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 3】SQLAlchemy Eager Loading")
    logger.info("="*60)

    with Session(engine) as session:
        # ---- joinedload ----
        logger.info("\n--- joinedload（LEFT JOIN，一次查询）---")

        def joined_load():
            users = session.query(User).options(
                joinedload(User.orders)  # 用 JOIN 预加载订单
            ).limit(10).all()
            return [(u.name, len(u.orders)) for u in users]

        result, query_count = count_queries(engine, joined_load)
        logger.info(f"查询 {len(result)} 个用户，执行了 {query_count} 次 SQL")

        # ---- selectinload ----
        logger.info("\n--- selectinload（IN 子查询，两次查询）---")

        def selectin_load():
            users = session.query(User).options(
                selectinload(User.orders)  # 用 IN 预加载订单
            ).limit(10).all()
            return [(u.name, len(u.orders)) for u in users]

        result, query_count = count_queries(engine, selectin_load)
        logger.info(f"查询 {len(result)} 个用户，执行了 {query_count} 次 SQL")

        # ---- 对比：默认 lazy loading ----
        logger.info("\n--- lazy loading（默认，N+1 问题）---")

        def lazy_load():
            users = session.query(User).limit(10).all()
            return [(u.name, len(u.orders)) for u in users]

        result, query_count = count_queries(engine, lazy_load)
        logger.info(f"查询 {len(result)} 个用户，执行了 {query_count} 次 SQL")


# ============================================================
# Part 4: EXPLAIN 查询计划
# ============================================================
def demo_explain(engine):
    """用 EXPLAIN 查看查询计划"""
    logger.info("\n" + "="*60)
    logger.info("【Part 4】EXPLAIN 查询计划分析")
    logger.info("="*60)

    with Session(engine) as session:
        queries = [
            ("简单查询", "SELECT * FROM users WHERE id = 42"),
            ("JOIN 查询", """
                SELECT u.name, o.product, o.amount
                FROM users u
                JOIN orders o ON u.id = o.user_id
                WHERE u.id = 42
            """),
            ("聚合查询", """
                SELECT u.name, COUNT(o.id), SUM(o.amount)
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id
                GROUP BY u.id
                ORDER BY SUM(o.amount) DESC
                LIMIT 10
            """),
        ]

        for label, sql in queries:
            logger.info(f"\n--- {label} ---")
            logger.info(f"SQL: {sql.strip()}")
            result = session.execute(text(f"EXPLAIN ANALYZE {sql}"))
            for row in result:
                logger.info(f"  {row}")


# ============================================================
# 主程序
# ============================================================
def main():
    engine = create_engine("postgresql+psycopg2://postgres:123456@localhost:5432/postgres", echo=False)

    with Session(engine) as session:
        init_data(session, engine)

    demo_n_plus_one(engine)
    demo_join_solution(engine)
    demo_eager_loading(engine)
    demo_explain(engine)

    logger.info("\n" + "="*60)
    logger.info("【总结】查询优化三板斧")
    logger.info("="*60)
    logger.info("""
    1. 避免 N+1：用 Eager Loading（joinedload / selectinload）
       → joinedload：适合一对一/多对一（LEFT JOIN）
       → selectinload：适合一对多（IN 子查询，更通用）

    2. 用 EXPLAIN ANALYZE 分析查询计划
       → 关注 Seq Scan（全表扫描）→ 加索引
       → 关注 Nested Loop → 考虑改为 Hash Join
       → 关注 rows 估算 vs 实际行数 → 更新统计信息

    3. 常见优化手段：
       → 加索引（覆盖高频查询）
       → 避免 SELECT *（只取需要的列）
       → 分页查询（LIMIT + OFFSET / keyset pagination）
       → 批量操作（bulk_insert / bulk_update）
    """)


if __name__ == "__main__":
    main()
