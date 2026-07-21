"""
Demo2: Redis 会话持久化（生产级 Agent 记忆方案）
功能：Redis 存储会话历史 → 跨会话记忆恢复 → 会话过期管理
核心：用 Redis 实现 Agent 长期记忆 + 会话持久化
依赖：redis（已安装）
注意：需要 Redis 服务运行（docker run -d -p 6379:6379 redis）
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import json
import time
from datetime import datetime


# ========== 1. Redis 连接 ==========
def get_redis_client():
    """获取 Redis 连接"""
    import redis
    try:
        client = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True,  # 自动解码为字符串
        )
        client.ping()  # 测试连接
        print("[OK] Redis 连接成功")
        return client
    except redis.ConnectionError:
        print("[WARN] Redis 未运行，使用模拟模式")
        print("  启动 Redis: docker run -d -p 6379:6379 redis")
        return None


# ========== 2. 会话存储类 ==========
class RedisSessionStore:
    """
    Redis 会话存储
    - 每个用户一个 session（按 user_id 隔离）
    - 会话自动过期（TTL）
    - 支持消息历史 + 用户画像
    """

    def __init__(self, redis_client, ttl: int = 3600):
        """
        Args:
            redis_client: Redis 连接
            ttl: 会话过期时间（秒），默认 1 小时
        """
        self.redis = redis_client
        self.ttl = ttl

    def _key(self, user_id: str, data_type: str = "session") -> str: 
        #data_type 用于区分不同类型的数据，如 "session" 表示会话数据，"profile" 表示用户画像数据
        """生成 Redis key"""
        return f"agent:{data_type}:{user_id}"

    # ---- 消息历史 ----
    def save_message(self, user_id: str, role: str, content: str):
        """保存一条消息到会话历史"""
        key = self._key(user_id, "messages")
        message = json.dumps({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }, ensure_ascii=False) #ensure_ascii=False 确保中文字符不会被转义为 Unicode 编码，而是以原始字符形式存储在 JSON 字符串中，这样在 Redis 中查看时会更直观。
        # RPUSH 追加到列表末尾
        self.redis.rpush(key, message)
        # 设置过期时间
        self.redis.expire(key, self.ttl)

    def get_messages(self, user_id: str, limit: int = 20) -> list[dict]:
        """获取最近 N 条消息"""
        key = self._key(user_id, "messages")
        # LLEN 获取列表长度.
        length = self.redis.llen(key)
        if length == 0:
            return []
        # LRANGE 获取最近 N 条
        start = max(0, length - limit)
        raw_messages = self.redis.lrange(key, start, -1)
        return [json.loads(m) for m in raw_messages]

    def clear_messages(self, user_id: str):
        """清空会话历史"""
        key = self._key(user_id, "messages")
        self.redis.delete(key)

    # ---- 用户画像（长期记忆） ----
    def save_user_profile(self, user_id: str, profile: dict):
        """保存用户画像"""
        key = self._key(user_id, "profile")
        self.redis.set(key, json.dumps(profile, ensure_ascii=False))
        self.redis.expire(key, 86400 * 7)  # 7 天过期

    def get_user_profile(self, user_id: str) -> dict:
        """获取用户画像"""
        key = self._key(user_id, "profile")
        data = self.redis.get(key)
        return json.loads(data) if data else {}

    # ---- 会话统计 ----
    def get_session_info(self, user_id: str) -> dict:
        """获取会话信息"""
        msg_count = self.redis.llen(self._key(user_id, "messages"))
        ttl = self.redis.ttl(self._key(user_id, "messages"))
        return {
            "user_id": user_id,
            "message_count": msg_count,
            "ttl_seconds": ttl,
        }


# ========== 3. 模拟 Redis（无 Redis 时的演示） ==========
class MockSessionStore:
    """内存模拟的会话存储（无 Redis 时使用）"""

    def __init__(self, ttl: int = 3600):
        self.store = {}  # user_id → {messages: [], profile: {}}
        self.ttl = ttl

    def save_message(self, user_id: str, role: str, content: str):
        if user_id not in self.store:
            self.store[user_id] = {"messages": [], "profile": {}}
        self.store[user_id]["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

    def get_messages(self, user_id: str, limit: int = 20) -> list[dict]:
        if user_id not in self.store:
            return []
        return self.store[user_id]["messages"][-limit:]

    def clear_messages(self, user_id: str):
        if user_id in self.store:
            self.store[user_id]["messages"] = []

    def save_user_profile(self, user_id: str, profile: dict):
        if user_id not in self.store:
            self.store[user_id] = {"messages": [], "profile": {}}
        self.store[user_id]["profile"] = profile

    def get_user_profile(self, user_id: str) -> dict:
        if user_id not in self.store:
            return {}
        return self.store[user_id]["profile"]

    def get_session_info(self, user_id: str) -> dict:
        count = len(self.store.get(user_id, {}).get("messages", []))
        return {"user_id": user_id, "message_count": count, "ttl_seconds": self.ttl}


# ========== 4. 演示会话管理 ==========
def demo_session_management(store):
    """演示会话管理功能"""
    print(f"\n{'=' * 60}")
    print("【会话管理演示】")
    print("=" * 60)

    user_id = "user-001"

    # 保存对话历史
    print(f"\n--- 保存对话历史 ---")
    store.save_message(user_id, "user", "你好，我叫张三")
    store.save_message(user_id, "assistant", "你好张三！很高兴认识你。")
    store.save_message(user_id, "user", "我喜欢 Python 编程")
    store.save_message(user_id, "assistant", "Python 是很好的语言！你主要用它做什么？")
    store.save_message(user_id, "user", "我在学 AI Agent 开发")
    store.save_message(user_id, "assistant", "太棒了！Agent 开发是当前的热门方向。")

    # 查询历史
    print(f"\n--- 查询历史（最近 4 条） ---")
    messages = store.get_messages(user_id, limit=4)
    for msg in messages:
        role = "用户" if msg["role"] == "user" else "AI"
        print(f"  [{role}] {msg['content']}")

    # 会话信息
    print(f"\n--- 会话信息 ---")
    info = store.get_session_info(user_id)
    print(f"  用户: {info['user_id']}")
    print(f"  消息数: {info['message_count']}")


# ========== 5. 演示用户画像 ==========
def demo_user_profile(store):
    """演示用户画像（长期记忆）"""
    print(f"\n{'=' * 60}")
    print("【用户画像（长期记忆）】")
    print("=" * 60)

    user_id = "user-001"

    # 保存用户画像
    profile = {
        "name": "张三",
        "interests": ["Python", "AI Agent", "LangGraph"],
        "skill_level": "中级",
        "last_topic": "Agent Memory",
        "interaction_count": 6,
    }
    store.save_user_profile(user_id, profile)
    print(f"\n--- 保存用户画像 ---")
    for k, v in profile.items():
        print(f"  {k}: {v}")

    # 读取用户画像
    print(f"\n--- 读取用户画像 ---")
    loaded = store.get_user_profile(user_id)
    for k, v in loaded.items():
        print(f"  {k}: {v}")


# ========== 6. 演示跨会话恢复 ==========
def demo_cross_session(store):
    """演示跨会话记忆恢复"""
    print(f"\n{'=' * 60}")
    print("【跨会话记忆恢复】")
    print("=" * 60)

    user_id = "user-002"

    # 第一次会话
    print(f"\n--- 第一次会话 ---")
    store.save_message(user_id, "user", "我是一名后端工程师")
    store.save_message(user_id, "assistant", "了解，你主要用什么技术栈？")
    store.save_message(user_id, "user", "Python + FastAPI + PostgreSQL")
    store.save_message(user_id, "assistant", "很好的组合！")

    print(f"  保存了 4 条消息")

    # 模拟会话断开，重新连接
    print(f"\n--- 模拟会话断开 ---")
    print(f"  （用户关闭浏览器，过了 10 分钟重新打开）")

    # 第二次会话：加载历史
    print(f"\n--- 第二次会话：加载历史 ---")
    history = store.get_messages(user_id, limit=5)
    print(f"  加载了 {len(history)} 条历史消息:")
    for msg in history:
        role = "用户" if msg["role"] == "user" else "AI"
        print(f"    [{role}] {msg['content']}")

    print(f"\n  → Agent 可以基于历史继续对话，不用从头开始")


# ========== 7. 展示 Redis 在 Agent 中的应用 ==========
def show_redis_in_agent():
    """展示 Redis 在 Agent 中的应用场景"""
    print("=" * 60)
    print("【Redis 在 Agent 中的应用】")
    print("=" * 60)
    print("""
    1. 会话持久化（本节 Demo）
       - 存储对话历史
       - 跨会话记忆恢复
       - 会话过期管理

    2. 缓存（Week 4 详细讲）
       - 缓存 LLM 响应（相同问题不重复调用）
       - 缓存 Embedding 结果
       - 缓存工具调用结果

    3. 限流（Week 4 详细讲）
       - 限制用户请求频率
       - 防止 API 滥用

    4. 分布式锁
       - 多 Agent 协作时的任务分配
       - 防止重复执行

    Redis 数据结构在 Agent 中的用途：
       STRING → 简单键值（会话数据、缓存）
       LIST   → 消息历史（RPUSH + LRANGE）
       HASH   → 用户画像（HSET + HGETALL）
       SET    → 标签管理（用户兴趣、工具标签）
       ZSET   → 优先级队列（任务调度）
    """)


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        show_redis_in_agent()

        # 尝试连接 Redis
        redis_client = get_redis_client()

        if redis_client:
            # 使用真实 Redis
            store = RedisSessionStore(redis_client, ttl=3600)
        else:
            # 使用内存模拟
            print("  使用内存模拟模式演示（功能相同，数据不持久化）")
            store = MockSessionStore(ttl=3600)

        demo_session_management(store)
        demo_user_profile(store)
        demo_cross_session(store)

        print(f"\n{'=' * 60}")
        print("[OK] Redis 会话持久化 Demo 完成！")
        print("核心收获：")
        print("  1. Redis LIST 存储消息历史（RPUSH + LRANGE）")
        print("  2. Redis STRING 存储用户画像（SET + GET）")
        print("  3. TTL 实现会话自动过期")
        print("  4. thread_id / user_id 隔离不同用户")
        print("  5. 生产环境用 RedisCheckpointer 替代 MemorySaver")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
