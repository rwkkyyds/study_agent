"""
Demo1: Locust 压测框架基础使用

学习目标：
1. Locust 核心概念（HttpUser、@task、wait_time）
2. 压测指标解读（QPS、响应时间、百分位数）
3. Web UI 使用和报告分析

运行方式：
终端1：python demo1_locust_basics.py
终端2：locust -f demo1_locust_basics.py --host=http://localhost:8000
浏览器：http://localhost:8089
"""

import asyncio
import logging
import time
from typing import Dict

from fastapi import FastAPI
from locust import HttpUser, between, task
from pydantic import BaseModel

# ============= 配置日志 =============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= 被测试的 FastAPI 服务 =============

app = FastAPI(title="Locust 压测演示服务")


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str


class QueryResponse(BaseModel):
    """查询响应模型"""
    query: str
    response: str
    latency_ms: float


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """健康检查接口 - 最简单的接口，用于测试基础连通性"""
    return {"status": "healthy"}


@app.get("/fast")
async def fast_endpoint() -> Dict[str, str]:
    """快速响应接口 - 模拟缓存命中场景，几乎无延迟"""
    return {"message": "This is a fast endpoint", "data": "cached_result"}


@app.get("/slow")
async def slow_endpoint() -> Dict[str, str]:
    """慢速响应接口 - 模拟数据库查询或外部 API 调用"""
    await asyncio.sleep(0.5)  # 模拟 500ms 的处理时间
    return {"message": "This is a slow endpoint", "data": "db_query_result"}


@app.post("/query")
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """
    查询接口 - 模拟真实业务场景

    处理逻辑：
    1. 根据查询长度模拟不同的处理时间
    2. 短查询快速返回，长查询慢速返回
    """
    start_time = time.time()

    # 根据查询长度模拟不同处理时间
    query_length = len(request.query)
    if query_length < 10:
        processing_time = 0.1  # 短查询：100ms
    elif query_length < 50:
        processing_time = 0.3  # 中等查询：300ms
    else:
        processing_time = 0.8  # 长查询：800ms

    await asyncio.sleep(processing_time)

    latency_ms = (time.time() - start_time) * 1000

    return QueryResponse(
        query=request.query,
        response=f"Processed query: {request.query[:20]}...",
        latency_ms=round(latency_ms, 2)
    )


# ============= Locust 压测用户类 =============

class WebsiteUser(HttpUser):
    """
    Locust 压测用户类

    核心概念：
    - HttpUser: Locust 提供的 HTTP 客户端基类，模拟用户行为
    - wait_time: 每次任务执行后的等待时间（模拟真实用户思考时间）
    - @task: 标记为压测任务，可设置权重（数字越大，执行频率越高）
    """

    # between(1, 3) 表示每次任务执行后等待 1-3 秒（模拟用户思考）
    wait_time = between(1, 3)

    @task(3)  # 权重 3 - 这个任务执行频率最高
    def test_health_check(self):
        """
        测试健康检查接口

        self.client.get() 会自动记录响应时间、成功/失败状态
        Locust 会统计所有请求的 QPS、P50/P90/P99 延迟
        """
        self.client.get("/health")

    @task(2)  # 权重 2
    def test_fast_endpoint(self):
        """测试快速接口 - 模拟缓存命中"""
        with self.client.get("/fast", catch_response=True) as response:
            # catch_response=True 允许手动标记成功/失败
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)  # 权重 1 - 执行频率最低
    def test_slow_endpoint(self):
        """测试慢速接口 - 模拟数据库查询"""
        self.client.get("/slow")

    @task(2)
    def test_query_short(self):
        """测试短查询 - 快速响应"""
        self.client.post("/query", json={"query": "AI Agent"})

    @task(1)
    def test_query_long(self):
        """测试长查询 - 慢速响应"""
        long_query = "How to build a production-grade RAG system with LangChain and FastAPI?"
        self.client.post("/query", json={"query": long_query})


# ============= 主程序 =============

if __name__ == "__main__":
    """
    运行说明：

    1. 启动被测服务（本脚本）：
       python demo1_locust_basics.py

    2. 另开终端启动 Locust 压测：
       locust -f demo1_locust_basics.py --host=http://localhost:8000

    3. 浏览器访问 Locust Web UI：
       http://localhost:8089

    4. Web UI 设置：
       - Number of users: 100 (模拟 100 个并发用户)
       - Spawn rate: 10 (每秒增加 10 个用户)
       - Host: http://localhost:8000

    5. 开始压测后观察指标：
       - RPS (Requests Per Second): 每秒请求数
       - Response times: 响应时间分布图
       - P50/P90/P99: 百分位数延迟
       - Failures: 错误率
    """
    import uvicorn

    logger.info("启动 FastAPI 服务用于压测...")
    logger.info("服务地址: http://localhost:8000")
    logger.info("健康检查: http://localhost:8000/health")
    logger.info("\n压测步骤：")
    logger.info("1. 保持本服务运行")
    logger.info("2. 另开终端执行: locust -f demo1_locust_basics.py --host=http://localhost:8000")
    logger.info("3. 浏览器访问: http://localhost:8089")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
