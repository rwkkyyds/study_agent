"""
demo4_redis_ratelimit.py - 限流 + Pub/Sub

学习目标：
1. 固定窗口限流（简单但有边界问题）
2. 滑动窗口限流（生产级方案）
3. Redis Pub/Sub 消息机制
4. 限流与 Agent 集成

依赖：pip install redis
"""

import redis
import time
import json
import logging
import threading
import uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# ============================================================
# 1. 固定窗口限流（简单方案）
# ============================================================

def fixed_window_check(user_id: str, limit: int = 5, window: int = 60) -> bool:
    """
    固定窗口限流：每 window 秒内最多 limit 次请求

    原理：
    - key = ratelimit:{user_id}:{当前窗口时间戳}
    - 每次请求 INCR
    - 超过 limit 则拒绝

    问题：窗口边界处可能短暂允许 2x 流量
    """
    window_key = int(time.time()) // window # 计算当前窗口的时间戳
    key = f"ratelimit:fixed:{user_id}:{window_key}"

    current = r.incr(key)
    if current == 1:
        r.expire(key, window)  # 首次设置过期

    if current > limit:
        logger.warning(f"[限流] {user_id} 超过限制 ({current}/{limit})")
        return False

    logger.info(f"[通过] {user_id} ({current}/{limit})")
    return True


# ============================================================
# 2. 滑动窗口限流（生产级方案）
# ============================================================

def sliding_window_check(user_id: str, limit: int = 10, window: int = 60) -> bool:
    """
    滑动窗口限流：用 Sorted Set 实现精确限流

    原理：
    - key = ratelimit:sliding:{user_id}
    - 每次请求：ZADD 添加当前时间戳（用唯一 ID 作为成员名，避免并发时覆盖）
    - 删除窗口外的旧记录：ZREMRANGEBYSCORE
    - 统计窗口内请求数：ZCARD
    
    【BUG 修复】使用 uuid 作为成员名，时间戳作为分数
    原因：time.time() 精度有限，高速连续请求会导致时间戳重复，
          使得 zadd 覆盖而不是添加新元素，导致限流失效！
    """
    key = f"ratelimit:sliding:{user_id}"
    now = time.time()
    window_start = now - window

    # ✅ 用 UUID 确保每个请求都是唯一的成员，不会被覆盖
    request_id = str(uuid.uuid4())

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)  # 清除窗口外记录
    pipe.zadd(key, {request_id: now})             # 添加当前请求（唯一成员，分数是时间戳）
    pipe.zcard(key)                                # 统计请求数
    pipe.expire(key, window)                       # 设置过期
    results = pipe.execute()

    count = results[2]
    if count > limit:
        # 删除刚添加的记录（拒绝请求）
        r.zrem(key, request_id)
        logger.warning(f"[限流] {user_id} 超过限制 ({count}/{limit})")
        return False

    logger.info(f"[通过] {user_id} ({count}/{limit})")
    return True


# ============================================================
# 3. Redis Pub/Sub（发布/订阅）
# ============================================================

def demo_pubsub():
    """演示 Redis Pub/Sub 消息机制"""
    print("\n--- Pub/Sub 演示 ---")

    channel = "demo:agent_events"
    received = []

    # 订阅者（在另一个线程中运行）
    def subscriber():
        pubsub = r.pubsub() # 创建 Pub/Sub 对象
        pubsub.subscribe(channel) # 订阅指定频道 subscribe() 方法用于订阅一个或多个频道，参数可以是单个频道名称或频道列表
        for message in pubsub.listen(): # listen() 方法是一个生成器，持续监听订阅的频道，返回消息字典
            if message["type"] == "message": #message格式： 
        #eg: {'type': 'message', 'pattern': None, 'channel': 'demo:agent_events', 'data': '{"event": "tool_call", "tool": "web_search", "query": "AI Agent"}'}
                data = json.loads(message["data"])
                received.append(data)
                logger.info(f"[订阅者] 收到: {data}")
                if data.get("event") == "end":
                    break
        pubsub.unsubscribe(channel) # 取消订阅
        logger.info("[订阅者] 结束订阅")

    # 启动订阅线程
    sub_thread = threading.Thread(target=subscriber, daemon=True)
    sub_thread.start()
    time.sleep(0.1)  # 等待订阅就绪

    # 发布者
    events = [
        {"event": "tool_call", "tool": "web_search", "query": "AI Agent"},
        {"event": "tool_result", "result": "搜索结果..."},
        {"event": "end"},
    ]
    for event in events:
        r.publish(channel, json.dumps(event, ensure_ascii=False)) 
        # publish() 方法用于向指定频道发布消息，第一个参数是频道名称，第二个参数是消息内容（字符串）
        logger.info(f"[发布者] 发送: {event}")
        time.sleep(0.1)

    sub_thread.join(timeout=2)
    print(f"  收到 {len(received)} 条消息")


# ============================================================
# 4. Agent 限流集成示例
# ============================================================

def agent_with_rate_limit(user_id: str, query: str) -> str:
    """带限流的 Agent 调用"""
    if not sliding_window_check(user_id, limit=5, window=60):
        return "请求过于频繁，请稍后再试。"
    return f"Agent 回答：关于「{query}」的处理结果..."


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("demo4: Redis 限流 + Pub/Sub")
    print("=" * 60)

    try:
        r.ping()
    except redis.ConnectionError:
        print("[ERROR] 无法连接 Redis")
        exit(1)

    # 固定窗口限流测试
    print("\n--- 固定窗口限流（5次/60秒）---")
    for i in range(7):
        ok = fixed_window_check("user_001", limit=5, window=60)
        print(f"  请求{i+1}: {'通过' if ok else '拒绝'}")

    # 滑动窗口限流测试
    print("\n--- 滑动窗口限流（3次/10秒）---")
    for i in range(5):
        ok = sliding_window_check("user_002", limit=3, window=10)
        print(f"  请求{i+1}: {'通过' if ok else '拒绝'}")

    # Agent 限流集成
    print("\n--- Agent 限流集成 ---")
    for i in range(4):
        result = agent_with_rate_limit("user_003", f"问题{i+1}")
        print(f"  {result}")

    # Pub/Sub
    demo_pubsub()

    # 清理
    for key in r.keys("ratelimit:*"):
        r.delete(key)
