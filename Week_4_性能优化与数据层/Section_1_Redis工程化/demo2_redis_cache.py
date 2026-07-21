"""
demo2_redis_cache.py - 缓存策略（Cache-Aside 模式）

学习目标：
1. Cache-Aside 旁路缓存模式（读：先查缓存→miss则查DB→写缓存）
2. TTL 过期策略
3. 缓存穿透/击穿/雪崩概念
4. LLM 调用结果缓存（减少 API 调用）

依赖：pip install redis
"""

import redis
import json
import time
import hashlib
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# ============================================================
# 1. 模拟数据库（实际项目用 PostgreSQL）
# ============================================================

MOCK_DB = {
    "user:001": {"name": "张三", "role": "AI工程师"},
    "user:002": {"name": "李四", "role": "产品经理"},
    "user:003": {"name": "王五", "role": "数据分析师"},
}


def query_db(key: str) -> dict | None:
    """模拟数据库查询（有延迟）"""
    time.sleep(0.1)  # 模拟 DB 查询延迟
    return MOCK_DB.get(key)


# ============================================================
# 2. Cache-Aside 旁路缓存模式
# ============================================================

def cache_aside_read(key: str, ttl: int = 60) -> dict | None:
    """
    Cache-Aside 读模式（最常用的缓存策略）：
    1. 先查 Redis 缓存
    2. 命中 → 直接返回（快）
    3. 未命中 → 查 DB → 写入缓存 → 返回

    Args:
        key: 缓存键
        ttl: 过期时间（秒）
    """
    # Step 1: 查缓存
    cached = r.get(key)
    if cached:
        logger.info(f"[缓存命中] {key}")
        return json.loads(cached)

    # Step 2: 缓存未命中，查 DB
    logger.info(f"[缓存未命中] {key}，查询 DB...")
    data = query_db(key)
    if data is None:
        return None

    # Step 3: 写入缓存（带 TTL）
    r.setex(key, ttl, json.dumps(data, ensure_ascii=False))
    logger.info(f"[写入缓存] {key}，TTL={ttl}s")
    return data


def cache_aside_write(key: str, data: dict, ttl: int = 60):
    """
    Cache-Aside 写模式：
    1. 更新 DB
    2. 删除缓存（而非更新缓存，避免并发不一致）

    为什么删除而非更新？
    - 并发场景下，更新缓存可能导致脏数据
    - 删除缓存后，下次读时自动从 DB 加载最新数据
    """
    # Step 1: 更新 DB（模拟）
    MOCK_DB[key] = data
    logger.info(f"[DB更新] {key}")

    # Step 2: 删除缓存
    r.delete(key)
    logger.info(f"[缓存删除] {key}")


# ============================================================
# 3. LLM 调用结果缓存（减少 API 调用费用）
# ============================================================

def cache_llm_call(prompt: str, llm_func, ttl: int = 3600) -> str:
    """
    LLM 结果缓存：相同 prompt 不重复调用 API

    用 prompt 的 hash 作为缓存 key，避免 key 过长
    """
    cache_key = f"llm_cache:{hashlib.md5(prompt.encode()).hexdigest()}"

    # 查缓存
    cached = r.get(cache_key)
    if cached:
        logger.info(f"[LLM缓存命中] 节省一次 API 调用")
        return cached

    # 调用 LLM（实际 API）
    logger.info(f"[LLM缓存未命中] 调用 API...")
    result = llm_func(prompt)

    # 写入缓存
    r.setex(cache_key, ttl, result)
    return result


def mock_llm(prompt: str) -> str:
    """模拟 LLM 调用"""
    time.sleep(0.2)
    return f"回答：关于「{prompt}」的分析结果..."


# ============================================================
# 4. 缓存问题演示
# ============================================================

def demo_cache_problems():
    """缓存三大问题：穿透、击穿、雪崩"""
    print("\n--- 缓存问题概念 ---")
    print("""
    1. 缓存穿透：查询不存在的数据，缓存永远 miss，每次都打 DB
       解决：布隆过滤器 / 缓存空值

    2. 缓存击穿：热点 key 过期，大量请求同时打 DB
       解决：互斥锁 / 永不过期 + 后台刷新

    3. 缓存雪崩：大量 key 同时过期，DB 瞬间压力暴增
       解决：TTL 加随机偏移 / 多级缓存
    """)


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("demo2: Redis 缓存策略（Cache-Aside）")
    print("=" * 60)

    try:
        r.ping()
    except redis.ConnectionError:
        print("[ERROR] 无法连接 Redis")
        exit(1)

    # 测试 Cache-Aside
    print("\n--- Cache-Aside 读写演示 ---")
    for uid in ["user:001", "user:002", "user:004"]:
        result = cache_aside_read(uid, ttl=30)
        print(f"  {uid} → {result}")

    # 第二次读（命中缓存）
    print("\n--- 第二次读（命中缓存）---")
    result = cache_aside_read("user:001", ttl=30)
    print(f"  user:001 → {result}")

    # 更新（删除缓存）
    print("\n--- 更新数据 ---")
    cache_aside_write("user:001", {"name": "张三", "role": "AI架构师"})

    # LLM 缓存
    print("\n--- LLM 结果缓存 ---")
    for _ in range(3):
        result = cache_llm_call("什么是RAG", mock_llm)
        print(f"  结果: {result}")

    demo_cache_problems()

    # 清理
    for key in r.keys("user:*") + r.keys("llm_cache:*"):
        r.delete(key)
