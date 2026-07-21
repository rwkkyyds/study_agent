"""
demo3_redis_session.py - Redis 会话存储（Agent 对话历史持久化）

学习目标：
1. 用 Redis 存储 Agent 对话历史（替代 MemorySaver）
2. 会话 TTL 自动过期（防止内存无限增长）
3. 会话管理：创建/读取/删除/列表
4. 生产级方案对比：MemorySaver vs Redis

依赖：pip install redis
"""

import redis
import json
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

SESSION_PREFIX = "session:"
SESSION_TTL = 3600  # 会话过期时间：1小时

# ============================================================
# 1. 会话 CRUD 操作
# ============================================================

def create_session(session_id: str, user_name: str = "用户") -> str:
    """创建新会话"""
    key = f"{SESSION_PREFIX}{session_id}"
    session_data = {
        "session_id": session_id,
        "user_name": user_name,
        "created_at": datetime.now().isoformat(),
        "messages": [],
    }
    r.setex(key, SESSION_TTL, json.dumps(session_data, ensure_ascii=False))
    logger.info(f"[创建会话] {session_id}，用户: {user_name}")
    return session_id


def add_message(session_id: str, role: str, content: str):
    """向会话添加消息"""
    key = f"{SESSION_PREFIX}{session_id}"
    data = r.get(key)
    if not data:
        logger.warning(f"会话 {session_id} 不存在")
        return

    session = json.loads(data)
    session["messages"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })

    # 更新缓存（刷新 TTL）
    r.setex(key, SESSION_TTL, json.dumps(session, ensure_ascii=False))
    logger.info(f"[添加消息] {session_id}: {role} → {content[:30]}...")


def get_history(session_id: str, limit: int = 10) -> list:
    """获取会话历史（最近 N 条）"""
    key = f"{SESSION_PREFIX}{session_id}"
    data = r.get(key)
    if not data:
        return []

    session = json.loads(data)
    return session["messages"][-limit:]


def get_session_info(session_id: str) -> dict | None:
    """获取会话元信息"""
    key = f"{SESSION_PREFIX}{session_id}"
    data = r.get(key)
    if not data:
        return None

    session = json.loads(data)
    return {
        "session_id": session["session_id"],
        "user_name": session["user_name"],
        "message_count": len(session["messages"]),
        "created_at": session["created_at"],
        "ttl": r.ttl(key),
    }


def delete_session(session_id: str):
    """删除会话"""
    key = f"{SESSION_PREFIX}{session_id}"
    r.delete(key)
    logger.info(f"[删除会话] {session_id}")


def list_sessions() -> list:
    """列出所有活跃会话"""
    keys = r.keys(f"{SESSION_PREFIX}*")
    sessions = []
    for key in keys:
        data = r.get(key)
        if data:
            session = json.loads(data)
            sessions.append({
                "session_id": session["session_id"],
                "user_name": session["user_name"],
                "message_count": len(session["messages"]),
                "ttl": r.ttl(key),
            })
    return sessions


# ============================================================
# 2. 模拟 Agent 多轮对话
# ============================================================

def simulate_agent_chat(session_id: str, user_msg: str) -> str:
    """模拟 Agent 处理用户消息（含历史上下文）"""
    # 添加用户消息
    add_message(session_id, "user", user_msg)

    # 获取历史上下文
    history = get_history(session_id, limit=5)
    context = "\n".join(f"{m['role']}: {m['content']}" for m in history)

    # 模拟 Agent 回复
    ai_reply = f"收到你的消息「{user_msg}」，这是我们的第 {len(history)} 条对话。"

    # 添加 AI 回复
    add_message(session_id, "assistant", ai_reply)
    return ai_reply


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("demo3: Redis 会话存储（Agent 对话历史）")
    print("=" * 60)

    try:
        r.ping()
    except redis.ConnectionError:
        print("[ERROR] 无法连接 Redis")
        exit(1)

    # 创建会话并模拟多轮对话
    sid = "chat_001"
    create_session(sid, user_name="张三")

    print("\n--- 模拟多轮对话 ---")
    for msg in ["你好", "什么是RAG", "帮我写个FastAPI接口"]:
        reply = simulate_agent_chat(sid, msg)
        print(f"  用户: {msg}")
        print(f"  AI: {reply}")

    # 查看会话信息
    print("\n--- 会话信息 ---")
    info = get_session_info(sid)
    print(f"  会话ID: {info['session_id']}")
    print(f"  用户: {info['user_name']}")
    print(f"  消息数: {info['message_count']}")
    print(f"  剩余TTL: {info['ttl']}秒")

    # 查看历史
    print("\n--- 对话历史 ---")
    for m in get_history(sid):
        print(f"  [{m['role']}] {m['content']}")

    # 多用户隔离
    print("\n--- 多用户隔离 ---")
    create_session("chat_002", "李四")
    simulate_agent_chat("chat_002", "我是另一个用户")
    sessions = list_sessions()
    for s in sessions:
        print(f"  {s['session_id']}: {s['user_name']} ({s['message_count']}条, TTL:{s['ttl']}s)")

    # 清理
    delete_session("chat_001")
    delete_session("chat_002")
