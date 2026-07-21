"""
demo4_async_db.py — async SQLAlchemy 异步数据库操作

学习目标：
1. 使用 async SQLAlchemy（AsyncEngine + AsyncSession）
2. 并发执行多个数据库查询（asyncio.gather）
3. 串行 vs 并发 DB 查询的性能对比

运行：python demo4_async_db.py
前置：pip install sqlalchemy[asyncio] aiosqlite
"""

import asyncio
import time
import logging
from sqlalchemy import Column, Integer, String, text, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession #async_sessionmaker 创建异步会话工厂，AsyncSession 异步会话
from sqlalchemy.orm import DeclarativeBase

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# 用 SQLite 做演示（零依赖，无需 Docker）
# 生产换成：postgresql+asyncpg://postgres:123456@localhost:5432/postgres
DB_URL = "sqlite+aiosqlite:///demo_async.db"


# ──────────────────────────────────────────────
# ORM 模型
# ──────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<Product {self.name} ¥{self.price}>"


# ──────────────────────────────────────────────
# Step 1：创建异步引擎和会话
# ──────────────────────────────────────────────
async def init_db():
    """
    【create_async_engine】创建异步数据库引擎
    连接串用 sqlite+aiosqlite（异步 SQLite 驱动）
    生产环境：postgresql+asyncpg://user:pwd@host/db
    """
    engine = create_async_engine(DB_URL, echo=False)

    # 建表
    async with engine.begin() as conn: #engine.begin() 返回一个异步上下文管理器，conn 是 AsyncConnection 对象
        await conn.run_sync(Base.metadata.create_all) # run_sync() 在异步上下文中运行同步函数，这里创建表结构

    # 【async_sessionmaker】工厂函数，每次调用产生一个新的 AsyncSession
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False) 
    #expire_on_commit=False 提交后不失效，避免再次访问时触发懒加载查询
    return engine, AsyncSessionLocal


# ──────────────────────────────────────────────
# Step 2：插入测试数据
# ──────────────────────────────────────────────
async def seed_data(session_factory):
    """插入 10 条商品数据"""
    products = [
        Product(name=f"商品-{i}", price=i * 100)
        for i in range(1, 11)
    ]
    async with session_factory() as session:
        session.add_all(products)
        await session.commit()
        logger.info(f"✅ 已插入 {len(products)} 条商品")


# ──────────────────────────────────────────────
# Step 3：串行查询 vs 并发查询
# ──────────────────────────────────────────────
async def query_product(session_factory, product_id: int) -> dict:
    """模拟一次 DB 查询（加 0.1s 延迟模拟网络+查询耗时）"""
    async with session_factory() as session:
        await asyncio.sleep(0.1)  # 模拟网络延迟
        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        p = result.scalar_one_or_none()
        return {"id": p.id, "name": p.name} if p else None


async def demo_serial_vs_concurrent_db(session_factory):
    """核心对比：串行查 10 个商品 vs 并发查 10 个商品"""
    ids = list(range(1, 11))  # 查 10 个商品

    # ── 串行 ──
    logger.info("\n── 串行查询（逐个 await）──")
    t0 = time.perf_counter()
    results = []
    for pid in ids:
        r = await query_product(session_factory, pid)
        results.append(r)
    serial = time.perf_counter() - t0
    logger.info(f"  串行耗时：{serial:.2f}s（{len(ids)} 次查询 × 0.1s = {len(ids)*0.1:.1f}s）")

    # ── 并发 ──
    logger.info("\n── 并发查询（gather 同时发起）──")
    t0 = time.perf_counter()
    results = await asyncio.gather(
        *(query_product(session_factory, pid) for pid in ids)
    )
    concurrent = time.perf_counter() - t0
    logger.info(f"  并发耗时：{concurrent:.2f}s（≈ 单次查询 0.1s）")
    logger.info(f"  加速比：{serial / concurrent:.1f}x")


# ──────────────────────────────────────────────
# Step 4：事务内的并发操作
# ──────────────────────────────────────────────
async def demo_concurrent_insert(session_factory):
    """并发插入 + 事务演示"""
    logger.info("\n── 并发插入 ──")

    async def insert_one(name: str, price: int):
        async with session_factory() as session:
            session.add(Product(name=name, price=price))
            await asyncio.sleep(0.05)  # 模拟写入延迟
            await session.commit()
            logger.info(f"  已插入 {name}")

    t0 = time.perf_counter()
    await asyncio.gather(
        insert_one("新品-A", 999),
        insert_one("新品-B", 888),
        insert_one("新品-C", 777),
    )
    elapsed = time.perf_counter() - t0
    logger.info(f"  3 次并发插入耗时：{elapsed:.2f}s")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
async def main():
    engine, session_factory = await init_db()
    try:
        await seed_data(session_factory)
        await demo_serial_vs_concurrent_db(session_factory)
        await demo_concurrent_insert(session_factory)
    finally:
        await engine.dispose()
        logger.info("数据库连接已释放")


if __name__ == "__main__":
    asyncio.run(main())
    print("\n✅ demo4 完成！")
