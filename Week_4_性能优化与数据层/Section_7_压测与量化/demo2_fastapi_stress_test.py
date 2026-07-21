"""
Demo2: FastAPI 真实业务场景压测

学习目标：
1. 对包含数据库操作的 API 进行压测
2. 对比优化前后的性能差异（连接池、缓存、索引）
3. 定位性能瓶颈并量化优化效果

核心场景：
- 用户查询接口（带数据库和缓存）
- 优化前：单连接 + 无缓存
- 优化后：连接池 + Redis 缓存
"""

import asyncio
import json
import logging
import random
import time
from typing import Dict, List, Optional

import redis
from fastapi import FastAPI, HTTPException
from locust import HttpUser, between, task
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

# ============= 配置日志 =============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= 数据库模型 =============

Base = declarative_base()


class Article(Base):
    """文章表 - 模拟知识库"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), index=True)  # 添加索引加速查询


# ============= 配置数据库连接池 =============

# 优化后的数据库引擎配置
engine = create_engine(
    "sqlite:///./stress_test.db",
    poolclass=QueuePool,  # 使用连接池
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 最大溢出连接数
    pool_pre_ping=True,  # 连接前检查可用性
    pool_recycle=3600,  # 连接回收时间（1小时）
)

SessionLocal = sessionmaker(bind=engine)

# 创建表
Base.metadata.create_all(bind=engine)

# ============= Redis 缓存 =============

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True,
    socket_connect_timeout=5
)

CACHE_TTL = 300  # 缓存 5 分钟

# ============= Pydantic 模型 =============


class ArticleQuery(BaseModel):
    """查询请求"""
    keyword: str
    use_cache: bool = True  # 是否使用缓存


class ArticleResponse(BaseModel):
    """查询响应"""
    articles: List[Dict]
    total: int
    from_cache: bool
    latency_ms: float


# ============= FastAPI 应用 =============

app = FastAPI(title="FastAPI 压测演示")


def init_demo_data():
    """初始化测试数据"""
    db = SessionLocal()
    try:
        # 检查是否已有数据
        count = db.query(Article).count()
        if count > 0:
            logger.info(f"数据库已有 {count} 条数据，跳过初始化")
            return

        # 生成 1000 条测试数据
        categories = ["AI", "Python", "Database", "Web", "DevOps"]
        articles = []

        for i in range(1000):
            article = Article(
                title=f"Article {i}: {random.choice(categories)} Tutorial",
                content=f"Content for article {i}. " * 20,  # 模拟长文本
                category=random.choice(categories)
            )
            articles.append(article)

        db.bulk_save_objects(articles)  
         #批量提交多个 ORM 实例对象，单条事务一次性写入数据库，相比循环db.session.add()再 commit 性能更高，减少多次 IO。
        db.commit()
        logger.info("成功初始化 1000 条测试数据")

    except Exception as e:
        logger.error(f"初始化数据失败: {e}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup") 
async def startup_event():
    """应用启动时初始化数据"""
    init_demo_data()
    logger.info("FastAPI 应用启动完成")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "db": "connected"}


@app.post("/search", response_model=ArticleResponse)
async def search_articles(query: ArticleQuery):
    """
    文章搜索接口 - 支持缓存优化

    性能优化点：
    1. Redis 缓存热门查询
    2. 数据库连接池复用连接
    3. 索引加速查询
    """
    start_time = time.time()

    cache_key = f"search:{query.keyword}"

    # 尝试从缓存获取
    if query.use_cache:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                latency_ms = (time.time() - start_time) * 1000
                result = json.loads(cached_data)
                result["from_cache"] = True
                result["latency_ms"] = round(latency_ms, 2)
                return ArticleResponse(**result)
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")

    # 缓存未命中，查询数据库
    db = SessionLocal()
    try:
        # 模拟复杂查询
        articles_query = db.query(Article).filter(
            Article.title.contains(query.keyword) #contains() 方法用于生成 SQL LIKE 查询，匹配包含指定关键字的标题
        ).limit(10)

        articles = articles_query.all()

        result_data = {
            "articles": [
                {"id": a.id, "title": a.title, "category": a.category}
                for a in articles
            ],
            "total": len(articles),
            "from_cache": False,
            "latency_ms": 0
        }

        # 写入缓存
        if query.use_cache:
            try:
                redis_client.setex(
                    cache_key,
                    CACHE_TTL,
                    json.dumps(result_data)
                )
            except Exception as e:
                logger.warning(f"缓存写入失败: {e}")

        latency_ms = (time.time() - start_time) * 1000
        result_data["latency_ms"] = round(latency_ms, 2)

        return ArticleResponse(**result_data)

    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============= Locust 压测用户 =============

class APIUser(HttpUser):
    """
    模拟真实用户行为

    测试场景：
    1. 热门关键词查询（缓存命中率高）
    2. 随机关键词查询（缓存命中率低）
    3. 对比有缓存 vs 无缓存的性能差异
    """

    wait_time = between(0.5, 2)

    # 热门关键词（模拟热点数据）
    hot_keywords = ["AI", "Python", "Database"]

    # 随机关键词
    random_keywords = [
        "Tutorial", "Guide", "Introduction",
        "Advanced", "Best Practices", "Tips"
    ]

    @task(5)  # 权重 5 - 热门查询占主要流量
    def search_hot_keywords_with_cache(self):
        """搜索热门关键词（使用缓存）- 模拟 80% 的流量"""
        keyword = random.choice(self.hot_keywords)
        self.client.post(
            "/search",
            json={"keyword": keyword, "use_cache": True},
            name="/search [cache-hot]"
        )

    @task(2)  # 权重 2
    def search_random_keywords_with_cache(self):
        """搜索随机关键词（使用缓存）"""
        keyword = random.choice(self.random_keywords)
        self.client.post(
            "/search",
            json={"keyword": keyword, "use_cache": True},
            name="/search [cache-random]"
        )

    @task(1)  # 权重 1 - 对比无缓存场景
    def search_without_cache(self):
        """搜索不使用缓存 - 用于对比性能差异"""
        keyword = random.choice(self.hot_keywords)
        self.client.post(
            "/search",
            json={"keyword": keyword, "use_cache": False},
            name="/search [no-cache]"
        )


# ============= 主程序 =============

if __name__ == "__main__":
    """
    运行步骤：

    1. 确保 Redis 已启动：
       docker run -d -p 6379:6379 redis:latest

    2. 启动 FastAPI 服务：
       python demo2_fastapi_stress_test.py

    3. 启动 Locust 压测：
       locust -f demo2_fastapi_stress_test.py --host=http://localhost:8001

    4. 浏览器访问 http://localhost:8089

    5. 观察指标对比：
       - /search (use_cache=True) vs (use_cache=False)
       - 缓存命中率提升多少性能？
       - P99 延迟降低多少？
    """
    import uvicorn

    logger.info("=" * 60)
    logger.info("FastAPI 压测演示服务启动中...")
    logger.info("=" * 60)
    logger.info("服务地址: http://localhost:8001")
    logger.info("健康检查: http://localhost:8001/health")
    logger.info("\n压测步骤：")
    logger.info("1. 确保 Redis 已启动（端口 6379）")
    logger.info("2. 保持本服务运行")
    logger.info("3. 执行: locust -f demo2_fastapi_stress_test.py --host=http://localhost:8001")
    logger.info("4. 访问: http://localhost:8089")
    logger.info("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")
