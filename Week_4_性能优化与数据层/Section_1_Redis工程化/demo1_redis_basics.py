"""
demo1_redis_basics.py - Redis 基础数据结构操作

学习目标：
1. 用 redis-py 连接 Redis（有组件用组件，不造轮子）
2. 掌握五种基础数据结构：String/Hash/List/Set/SortedSet
3. 理解 TTL 过期机制

依赖：pip install redis
前置：docker run -d -p 6379:6379 redis
"""

import redis
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# 1. 连接 Redis（redis-py 组件，不造轮子）
# ============================================================

def get_redis():
    """获取 Redis 连接（decode_responses=True 自动解码为字符串）"""
    return redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


# ============================================================
# 2. String 操作（最基础）
# ============================================================

def demo_string(r: redis.Redis):
    """String：键值对，支持过期时间"""
    print("\n--- String 操作 ---")

    # SET / GET
    r.set("demo:name", "AI Agent 助手")
    print(f"GET demo:name = {r.get('demo:name')}")

    # SETEX：带过期时间（秒）
    r.setex("demo:temp", 10, "10秒后过期")
    print(f"GET demo:temp = {r.get('demo:temp')}")
    print(f"TTL demo:temp = {r.ttl('demo:temp')} 秒")

    # INCR：原子计数器（限流场景用）
    r.set("demo:counter", 0)
    for _ in range(5): #_表示不关心循环变量
        r.incr("demo:counter")
    print(f"INCR 5次后 demo:counter = {r.get('demo:counter')}")

    # 清理
    r.delete("demo:name", "demo:temp", "demo:counter")


# ============================================================
# 3. Hash 操作（存储对象）
# ============================================================

def demo_hash(r: redis.Redis):
    """Hash：字段级操作，适合存储用户信息、会话状态"""
    print("\n--- Hash 操作 ---")

    # HSET：设置多个字段
    r.hset("demo:user:001", mapping={
        "name": "张三",
        "role": "AI工程师",
        "department": "技术部",
    })

    # HGET：获取单个字段
    print(f"HGET name = {r.hget('demo:user:001', 'name')}")

    # HGETALL：获取所有字段
    print(f"HGETALL = {r.hgetall('demo:user:001')}")

    # HINCRBY：原子递增
    r.hincrby("demo:user:001", "login_count", 1)
    r.hincrby("demo:user:001", "login_count", 1)
    print(f"login_count = {r.hget('demo:user:001', 'login_count')}")

    r.delete("demo:user:001")


# ============================================================
# 4. List 操作（消息队列、历史记录）
# ============================================================

def demo_list(r: redis.Redis):
    """List：有序列表，适合对话历史、任务队列"""
    print("\n--- List 操作 ---")

    key = "demo:chat_history"
    r.delete(key) # 清理旧数据 

    # LPUSH：左侧插入（最新消息在前）
    r.lpush(key, "用户: 你好")  #list 不用像string那样初始化用set，直接lpush就行,会自动创建
    r.lpush(key, "AI: 你好！有什么可以帮你？")
    r.lpush(key, "用户: 什么是RAG？")

    # LRANGE：获取范围（0=-1 表示全部）
    history = r.lrange(key, 0, -1)
    print(f"对话历史 ({len(history)} 条):")
    for msg in history:
        print(f"  {msg}")

    # LLEN：列表长度
    print(f"列表长度: {r.llen(key)}")

    # LTRIM：保留最近 N 条（防止无限增长）
    r.ltrim(key, 0, 9)  # 保留最近10条
    print(f"LTRIM 后长度: {r.llen(key)}")

    r.delete(key)


# ============================================================
# 5. Set 操作（去重、交集）
# ============================================================

def demo_set(r: redis.Redis):
    """Set：无序集合，适合标签、权限、去重"""
    print("\n--- Set 操作 ---")

    # SADD：添加成员
    r.sadd("demo:tags:article1", "RAG", "LangChain", "AI")
    r.sadd("demo:tags:article2", "RAG", "Milvus", "向量数据库")

    # SMEMBERS：获取所有成员
    print(f"文章1标签: {r.smembers('demo:tags:article1')}")
    print(f"文章2标签: {r.smembers('demo:tags:article2')}")

    # SINTER：交集（共同标签）
    common = r.sinter("demo:tags:article1", "demo:tags:article2")
    print(f"共同标签: {common}")

    # SUNION：并集
    all_tags = r.sunion("demo:tags:article1", "demo:tags:article2")
    print(f"所有标签: {all_tags}")

    r.delete("demo:tags:article1", "demo:tags:article2")


# ============================================================
# 6. 清理演示 key
# ============================================================

def cleanup(r: redis.Redis):
    """清理所有 demo 开头的 key"""
    keys = r.keys("demo:*") #keys() 方法返回所有匹配的 key 列表 
    if keys:
        r.delete(*keys) # delete() 方法可以一次删除多个 key，使用 *keys 解包列表
        logger.info(f"清理了 {len(keys)} 个 demo key")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("demo1: Redis 基础数据结构")
    print("=" * 60)

    try:
        r = get_redis()
        r.ping()
        logger.info("Redis 连接成功")

        demo_string(r)
        demo_hash(r)
        demo_list(r)
        demo_set(r)
        cleanup(r)

        print("\n总结：Redis 五种数据结构各有适用场景")
        print("  String: 缓存、计数器")
        print("  Hash:   对象存储（用户、会话状态）")
        print("  List:   对话历史、任务队列")
        print("  Set:    标签、权限、去重")
    except redis.ConnectionError:
        print("[ERROR] 无法连接 Redis，请先启动: docker run -d -p 6379:6379 redis")
