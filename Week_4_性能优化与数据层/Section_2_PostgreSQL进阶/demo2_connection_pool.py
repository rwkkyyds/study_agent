"""
demo2_connection_pool.py - PostgreSQL 连接池配置与监控

学习目标：
1. 理解为什么需要连接池（不复用连接的代价）
2. 掌握 SQLAlchemy 连接池核心参数
3. 学会监控连接池状态
4. 对比同步 vs 异步连接池

运行：python demo2_connection_pool.py
前置：PostgreSQL 已启动，密码 123456
"""

import logging
import time
import threading
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# PostgreSQL 连接
# ============================================================
DB_URL = "postgresql+psycopg2://postgres:123456@localhost:5432/postgres"
#psycopg2 是 PostgreSQL 官方推荐的 Python 驱动，性能稳定，支持同步操作

# ============================================================
# Part 1: 连接池核心概念
# ============================================================
def demo_pool_basics():
    """
    连接池 = 预先创建一批数据库连接，反复复用，避免每次查询都新建连接

    通俗理解：
        没有连接池：每次去银行都要取号、排队、办业务、离开 → 慢
        有连接池：你是 VIP 客户，银行给你预留了窗口 → 快
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 1】连接池基础概念")
    logger.info("="*60)

    engine = create_engine(
        DB_URL,
        # ---- 核心参数 ----
        pool_size=5,          # 连接池大小：同时保持 5 个空闲连接
        max_overflow=10,      # 最大溢出：pool_size 满了后，最多再创建 10 个
                              # 最大并发连接数 = 5 + 10 = 15
        pool_timeout=30,      # 获取连接超时：等 30 秒拿不到连接就报错
        pool_recycle=3600,    # 连接回收：连接超过 1 小时就重建（防 PostgreSQL 超时断开）
        pool_pre_ping=True,   # 使用前先 ping：检测连接是否有效
        echo=False,  #echo=True 可以打印 SQLAlchemy 执行的 SQL 语句，便于调试
    )

    # ---- 监听连接池事件 ----
    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn, connection_record):
        logger.info("  → 新连接被创建（数据库层面）")

    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_conn, connection_record, connection_proxy):
        logger.info("  → 从连接池借出连接")

    @event.listens_for(engine, "checkin")
    def on_checkin(dbapi_conn, connection_record):
        logger.info("  → 连接归还到连接池")

    # ---- 演示连接复用 ----
    logger.info("\n--- 第一次查询（创建连接）---")
    with Session(engine) as session:
        result = session.execute(text("SELECT 1")).scalar()
        logger.info(f"查询结果: {result}")

    logger.info("\n--- 第二次查询（复用连接）---")
    with Session(engine) as session:
        result = session.execute(text("SELECT 2")).scalar()
        logger.info(f"查询结果: {result}")

    # ---- 查看连接池状态 ----
    pool_status = engine.pool.status()
    logger.info(f"\n连接池状态: {pool_status}")
    logger.info(f"pool_size() = {engine.pool.size()}")
    logger.info(f"checkedin() = {engine.pool.checkedin()}") #checkedin() = 当前连接池中空闲的连接数
    logger.info(f"checkedout() = {engine.pool.checkedout()}") #checkedout() = 当前连接池中正在使用的连接数
    logger.info(f"overflow() = {engine.pool.overflow()}") #overflow() = 当前连接池中溢出的连接数（超过 pool_size 的连接数）

    engine.dispose() 
    #释放连接池中的所有连接，关闭数据库连接


# ============================================================
# Part 2: 并发场景下的连接池行为
# ============================================================
def demo_pool_concurrency():
    """
    模拟多个线程同时请求数据库连接

    场景：pool_size=3, max_overflow=2 → 最多 5 个并发连接
    第 6 个线程来了会等待（pool_timeout）或报错
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 2】并发场景下的连接池行为")
    logger.info("="*60)

    engine = create_engine(
        DB_URL,
        pool_size=3,          # 连接池大小：3
        max_overflow=2,       # 最大溢出：2 → 最大并发 5
        pool_timeout=5,       # 超时时间：5 秒
        echo=False,
    )

    # 建测试表
    with Session(engine) as session:
        session.execute(text("DROP TABLE IF EXISTS pool_test"))
        session.execute(text("""
            CREATE TABLE pool_test (
                id SERIAL PRIMARY KEY,
                worker_id INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        session.commit()

    results = []
    errors = []

    def worker(worker_id: int):
        """每个线程：借连接 → 执行写入 → 持有连接 0.5 秒 → 归还"""
        try:
            with Session(engine) as session:
                session.execute(
                    text("INSERT INTO pool_test (worker_id) VALUES (:wid)"),
                    {"wid": worker_id}
                )
                session.commit()
                time.sleep(0.5)  # 模拟耗时操作，持有连接
                results.append(worker_id)
                logger.info(f"  线程 {worker_id} 完成")
        except Exception as e:
            errors.append((worker_id, str(e)))
            logger.error(f"  线程 {worker_id} 失败: {type(e).__name__}")

    # ---- 启动 5 个线程（刚好在连接池容量内）----
    logger.info("\n--- 启动 5 个线程（最大并发 5）---")
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join() #等待所有线程完成  
    logger.info(f"成功: {len(results)} 个, 失败: {len(errors)} 个")

    # ---- 启动 8 个线程（超出连接池容量）----
    logger.info("\n--- 启动 8 个线程（超出最大并发 5）---")
    results.clear()
    errors.clear()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    logger.info(f"成功: {len(results)} 个, 失败: {len(errors)} 个")
    if errors:
        logger.info("超出连接池容量的线程会等待或超时报错")

    # 清理
    with Session(engine) as session:
        session.execute(text("DROP TABLE IF EXISTS pool_test"))
        session.commit()

    engine.dispose()


# ============================================================
# Part 3: 连接池参数速查
# ============================================================
def demo_pool_params():
    """连接池参数速查表"""
    logger.info("\n" + "="*60)
    logger.info("【Part 3】连接池参数速查表")
    logger.info("="*60)
    logger.info("""
    ┌─────────────────┬───────────┬─────────────────────────────────────────┐
    │ 参数             │ 默认值    │ 说明                                     │
    ├─────────────────┼───────────┼─────────────────────────────────────────┤
    │ pool_size       │ 5         │ 连接池保持的空闲连接数                    │
    │ max_overflow    │ 10        │ 超出 pool_size 后最多创建的额外连接       │
    │ pool_timeout    │ 30        │ 等待获取连接的超时秒数                    │
    │ pool_recycle    │ -1(不回收) │ 连接存活秒数，超时重建（建议 3600）       │
    │ pool_pre_ping   │ False     │ 使用前 ping 检测连接是否有效              │
    └─────────────────┴───────────┴─────────────────────────────────────────┘

    最大并发连接数 = pool_size + max_overflow

    生产环境建议（PostgreSQL）：
    → pool_size = CPU核心数 * 2 + 1（如 4核 → pool_size=9）
    → max_overflow = pool_size（允许突发流量）
    → pool_recycle = 3600（防 PostgreSQL 超时断开）
    → pool_pre_ping = True（防连接已断开但还在用）

    PostgreSQL 的 max_connections 默认 = 100
    → 如果你有 5 个服务实例，每个 pool_size=20 → 刚好用满 100
    → pool_size 要根据服务实例数来规划！
    """)


# ============================================================
# Part 4: 同步 vs 异步连接池
# ============================================================
def demo_async_pool_info():
    """同步 vs 异步连接池对比"""
    logger.info("\n" + "="*60)
    logger.info("【Part 4】同步 vs 异步连接池")
    logger.info("="*60)
    logger.info("""
    同步引擎（psycopg2）：              异步引擎（asyncpg）：
    ─────────────────────               ─────────────────────
    create_engine(                      create_async_engine(
      "postgresql+psycopg2://..."         "postgresql+asyncpg://..."
    )                                   )

    Session(engine)                     AsyncSession(async_engine)

    适用场景：
    → 同步：普通 Web 应用、脚本、后台任务
    → 异步：FastAPI + 高并发（不阻塞事件循环）

    性能对比：
    → asyncpg 比 psycopg2 快 2-5 倍（底层用 C 实现的异步协议）
    → FastAPI 中推荐：asyncpg + AsyncSession

    Demo 代码（FastAPI 中使用异步连接池）：

    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_engine = create_async_engine(
        "postgresql+asyncpg://postgres:123456@localhost/mydb",
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )

    AsyncSessionLocal = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )  #参数作用 class_=AsyncSession：指定使用异步会话类 expire_on_commit=False：提交后不失效对象，避免再次访问时触发懒加载

    async def get_db():
        async with AsyncSessionLocal() as session:
            yield session
    """ )


# ============================================================
# 主程序
# ============================================================
def main():
    demo_pool_basics()
    demo_pool_concurrency()
    demo_pool_params()
    demo_async_pool_info()

    logger.info("\n" + "="*60)
    logger.info("【总结】连接池 = 减少创建/销毁连接的开销")
    logger.info("="*60)
    logger.info("""
    1. pool_size：保持多少个空闲连接（根据 CPU 核心数和实例数调整）
    2. max_overflow：突发流量时最多创建多少额外连接
    3. pool_timeout：拿不到连接时等多久
    4. pool_recycle：连接活多久后重建（防数据库超时断开）
    5. pool_pre_ping：用之前先检测连接是否有效
    6. 高并发场景用 AsyncEngine + asyncpg
    """)


if __name__ == "__main__":
    main()
