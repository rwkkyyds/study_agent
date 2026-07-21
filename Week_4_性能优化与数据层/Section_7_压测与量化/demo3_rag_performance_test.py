"""
Demo3: RAG 系统端到端性能压测

学习目标：
1. 对完整 RAG 流程进行压测（Embedding + 向量检索 + LLM 生成）
2. 分析各环节耗时占比（瓶颈定位）
3. 量化批处理优化效果
4. 生产级性能指标分析（P99 延迟、吞吐量、错误率）

性能优化点：
- 批量 Embedding
- 向量检索并发
- 缓存热门查询
- 异步调用 LLM
"""

import asyncio
import json
import logging
import time
from typing import Dict, List

import numpy as np
import redis
from fastapi import FastAPI, HTTPException
from locust import HttpUser, between, task
from pydantic import BaseModel

# ============= 配置日志 =============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= 模拟组件 =============

class MockEmbeddingModel:
    """模拟 Embedding 模型"""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed_query(self, text: str) -> List[float]:
        """生成查询向量 - 模拟 50-100ms 的延迟"""
        time.sleep(0.05 + np.random.rand() * 0.05)  # 50-100ms
        return np.random.rand(self.dimension).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量 - 比单个快 3-5 倍"""
        time.sleep(0.02 * len(texts))  # 批处理更快
        return [np.random.rand(self.dimension).tolist() for _ in texts]


class MockVectorDB:
    """模拟向量数据库"""

    def __init__(self, num_docs: int = 10000):
        """初始化模拟向量库"""
        self.dimension = 384
        self.num_docs = num_docs
        # 模拟预存向量
        self.vectors = np.random.rand(num_docs, self.dimension).astype(np.float32)
        self.docs = [f"Document {i} content..." for i in range(num_docs)]

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict]:
        """
        向量检索 - 模拟 20-50ms 的延迟

        HNSW 索引性能：
        - 10K 文档：20-30ms
        - 100K 文档：30-50ms
        - 1M 文档：50-100ms
        """
        time.sleep(0.02 + np.random.rand() * 0.03)  # 20-50ms

        # 模拟相似度计算
        query_arr = np.array(query_vector)
        # 随机返回 top_k 个文档
        indices = np.random.choice(self.num_docs, top_k, replace=False)

        return [
            {
                "doc_id": int(idx),
                "content": self.docs[idx],
                "score": float(np.random.rand())
            }
            for idx in indices
        ]


class MockLLM:
    """模拟 LLM 调用"""

    async def agenerate(self, context: str, query: str) -> str:
        """
        异步生成回答 - 模拟 LLM 调用延迟

        延迟模拟：
        - OpenAI GPT-4: 1-3s（取决于 token 数量）
        - 本地模型：0.5-2s
        """
        await asyncio.sleep(0.5 + np.random.rand() * 1.5)  # 500ms-2s
        return f"Based on the context, here's the answer to: {query[:50]}..."


# ============= 初始化组件 =============

embedding_model = MockEmbeddingModel()
vector_db = MockVectorDB(num_docs=10000)
llm_model = MockLLM()

# Redis 缓存
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=1,
    decode_responses=True
)

CACHE_TTL = 600  # 缓存 10 分钟

# ============= Pydantic 模型 =============


class RAGQuery(BaseModel):
    """RAG 查询请求"""
    question: str
    top_k: int = 5
    use_cache: bool = True


class RAGResponse(BaseModel):
    """RAG 查询响应"""
    question: str
    answer: str
    retrieved_docs: List[Dict]
    from_cache: bool
    timings: Dict[str, float]  # 各环节耗时
    total_latency_ms: float


# ============= FastAPI 应用 =============

app = FastAPI(title="RAG 系统压测")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "vector_db": "connected",
        "redis": "connected"
    }


@app.post("/rag/query", response_model=RAGResponse)
async def rag_query(query: RAGQuery):
    """
    RAG 端到端查询接口

    处理流程：
    1. 查询缓存（命中则直接返回）
    2. 生成查询向量（Embedding）
    3. 向量检索（VectorDB.search）
    4. LLM 生成回答（基于检索上下文）
    5. 写入缓存
    """
    start_time = time.time()
    timings = {}

    cache_key = f"rag:{query.question}"

    # 1. 尝试缓存
    if query.use_cache:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                result = json.loads(cached)
                result["from_cache"] = True
                result["total_latency_ms"] = round((time.time() - start_time) * 1000, 2)
                return RAGResponse(**result)
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")

    # 2. Embedding 阶段
    t0 = time.time()
    query_vector = embedding_model.embed_query(query.question)
    timings["embedding_ms"] = round((time.time() - t0) * 1000, 2)

    # 3. 向量检索阶段
    t0 = time.time()
    retrieved_docs = vector_db.search(query_vector, top_k=query.top_k)
    timings["retrieval_ms"] = round((time.time() - t0) * 1000, 2)

    # 4. LLM 生成阶段
    t0 = time.time()
    context = "\n".join([doc["content"] for doc in retrieved_docs])
    answer = await llm_model.agenerate(context, query.question)
    timings["llm_ms"] = round((time.time() - t0) * 1000, 2)

    total_latency = round((time.time() - start_time) * 1000, 2)

    result = {
        "question": query.question,
        "answer": answer,
        "retrieved_docs": retrieved_docs,
        "from_cache": False,
        "timings": timings,
        "total_latency_ms": total_latency
    }

    # 5. 写入缓存
    if query.use_cache:
        try:
            redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")

    return RAGResponse(**result)


# ============= Locust 压测用户 =============

class RAGUser(HttpUser):
    """
    RAG 系统压测用户

    测试场景：
    1. 热门问题（高缓存命中率）
    2. 随机问题（低缓存命中率）
    3. 长问题 vs 短问题
    """

    wait_time = between(1, 3)

    # 热门问题（模拟重复查询）
    hot_questions = [
        "What is RAG?",
        "How does vector search work?",
        "What is LangChain?",
    ]

    # 随机问题
    random_questions = [
        "How to optimize embedding performance?",
        "What are the best practices for prompt engineering?",
        "How to deploy RAG system in production?",
        "What is the difference between FAISS and Milvus?",
        "How to evaluate RAG system performance?",
    ]

    @task(6)  # 权重 6 - 热门问题占大部分流量
    def query_hot_questions(self):
        """查询热门问题（缓存命中率高）"""
        import random
        question = random.choice(self.hot_questions)
        self.client.post(
            "/rag/query",
            json={"question": question, "use_cache": True},
            name=f"Query Hot"
        )

    @task(3)  # 权重 3
    def query_random_questions(self):
        """查询随机问题（缓存命中率低）"""
        import random
        question = random.choice(self.random_questions)
        self.client.post(
            "/rag/query",
            json={"question": question, "use_cache": True},
            name=f"Query Random"
        )

    @task(1)  # 权重 1 - 对比无缓存性能
    def query_without_cache(self):
        """查询不使用缓存"""
        import random
        question = random.choice(self.hot_questions)
        self.client.post(
            "/rag/query",
            json={"question": question, "use_cache": False},
            name=f"Query Without Cache"
        )


# ============= 主程序 =============

if __name__ == "__main__":
    """
    运行步骤：

    1. 启动 Redis：
       docker run -d -p 6379:6379 redis:latest

    2. 启动 FastAPI 服务：
       python demo3_rag_performance_test.py

    3. 启动 Locust 压测：
       locust -f demo3_rag_performance_test.py --host=http://localhost:8002

    4. 访问 http://localhost:8089
       - 建议设置：50 用户，5 用户/秒增长
       - 观察 P99 延迟变化

    5. 性能分析：
       - 查看 timings 各环节耗时占比
       - LLM 调用通常占 60-80% 时间
       - 缓存命中后延迟下降 90%+
    """
    import uvicorn

    logger.info("=" * 70)
    logger.info("RAG 系统性能压测服务启动中...")
    logger.info("=" * 70)
    logger.info("服务地址: http://localhost:8002")
    logger.info("健康检查: http://localhost:8002/health")
    logger.info("\n模拟配置：")
    logger.info("  - Embedding: 50-100ms")
    logger.info("  - 向量检索: 20-50ms")
    logger.info("  - LLM 生成: 500-2000ms")
    logger.info("  - 向量库文档数: 10,000")
    logger.info("\n压测步骤：")
    logger.info("1. 确保 Redis 已启动")
    logger.info("2. 执行: locust -f demo3_rag_performance_test.py --host=http://localhost:8002")
    logger.info("3. 访问: http://localhost:8089")
    logger.info("=" * 70)

    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="warning")
