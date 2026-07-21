"""
Demo1: LangGraph Checkpoint 机制（Agent 记忆基础）
功能：MemorySaver → Thread-based 会话 → State 持久化 → 多轮对话
核心：理解 Agent 短期记忆 + 工作记忆 + Checkpoint 持久化
依赖：langgraph（已安装）
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from typing import TypedDict, Annotated # 作用于类型注解，增强代码可读性和类型检查
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver 
#MemorySaver 是一个简单的内存 Checkpoint 实现，适合开发和测试环境使用。
# 它将每次运行的 State 保存在内存中，可以通过 thread_id 隔离不同会话的数据。
# 对于生产环境，建议使用 RedisCheckpointer 或 PostgreSQLCheckpointer 来实现更可靠的持久化存储。
import operator # 用于在条件边中指定状态更新的操作符，如 operator.add 表示累加


# ========== 1. Agent State ==========
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    user_name: str       # 用户名（工作记忆）
    task_count: int      # 任务计数（工作记忆）


# ========== 2. 节点函数 ==========
def chat_node(state: AgentState) -> dict:
    """聊天节点：模拟 LLM 回复"""
    user_msg = state["messages"][-1].content
    user_name = state.get("user_name", "用户")
    task_count = state.get("task_count", 0) + 1

    # 简单的回复逻辑（不调用 LLM，纯演示记忆机制）
    if "你好" in user_msg or "hello" in user_msg.lower():
        reply = f"你好 {user_name}！这是我们的第 {task_count} 次对话。"
    elif "名字" in user_msg:
        reply = f"你告诉我你叫 {user_name}。"
    elif "几次" in user_msg or "多少次" in user_msg:
        reply = f"我们已经对话了 {task_count} 次。"
    else:
        reply = f"收到你的消息：「{user_msg}」（第 {task_count} 次对话）"

    return {
        "messages": [AIMessage(content=reply)],
        "task_count": task_count,
    }


def set_name_node(state: AgentState) -> dict:
    """设置用户名节点"""
    user_msg = state["messages"][-1].content
    # 从消息中提取名字（简化处理）
    name = user_msg.replace("我叫", "").replace("我是", "").replace("我的名字是", "").strip()
    if not name:
        name = "用户"
    #task_count为什么不用变化？因为设置名字不算一次对话，所以 task_count 保持不变
    return {
        "user_name": name,
        "messages": [AIMessage(content=f"好的，我记住你叫 {name} 了！")],
    }


def should_set_name(state: AgentState) -> str:
    """条件路由：判断是否在设置名字（排除问句）"""
    user_msg = state["messages"][-1].content
    # 排除问句
    question_words = ["什么", "哪", "谁", "吗", "？", "?", "几", "怎么"]
    is_question = any(w in user_msg for w in question_words)
    # 匹配自我介绍
    is_intro = any(kw in user_msg for kw in ["我叫", "我是", "我的名字是"])
    if is_intro and not is_question:
        return "set_name"
    return "chat"


# ========== 3. 构建图 ==========
def build_agent():
    """构建带记忆的 Agent

    流程：START → router（条件路由） → set_name 或 chat → END

    为什么需要 router 节点？
    - START 只能有一个出边
    - 但需要根据用户消息决定走 set_name 还是 chat
    - 所以先到 router，再用条件边分流
    """
    graph = StateGraph(AgentState)

    # router 节点：不修改 State，仅作为条件路由的入口
    def router(state: AgentState) -> dict:
        return {}

    graph.add_node("router", router)
    graph.add_node("set_name", set_name_node)
    graph.add_node("chat", chat_node)

    # START → router → 条件分流
    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", should_set_name, { 
        "set_name": "set_name",
        "chat": "chat",
    })#参数解释,router: 条件路由节点名称, should_set_name: 条件函数, { "set_name": "set_name", "chat": "chat" }: 条件分支映射

    # 两个分支都到 END
    graph.add_edge("set_name", END)
    graph.add_edge("chat", END)

    return graph


# ========== 4. MemorySaver 演示 ==========
def demo_checkpoint():
    """演示 Checkpoint 持久化"""
    print("=" * 60)
    print("【Checkpoint 持久化演示】")
    print("=" * 60)

    # MemorySaver：内存中的 Checkpoint（开发用）
    # 生产环境用 RedisCheckpointer 或 PostgreSQLCheckpointer
    memory = MemorySaver() #memory 是一个简单的内存 Checkpoint 实现，适合开发和测试环境使用。

    graph = build_agent()
    # compile 时传入 checkpointer，自动保存每次运行的 State
    agent = graph.compile(checkpointer=memory)

    # thread_id：标识一个会话线程（类似 session_id）
    config = {"configurable": {"thread_id": "user-001"}}

    # ---- 第1轮对话 ----
    print("\n--- 第1轮：打招呼 ---")
    result = agent.invoke(
        {"messages": [HumanMessage(content="你好")], "user_name": "用户", "task_count": 0},
        config=config, #作用是传入配置参数，指定当前会话的 thread_id 为 "user-001"，用于在 MemorySaver 中隔离不同用户的会话数据
    )
    print(f"  AI: {result['messages'][-1].content}")
    print(f"  State: user_name={result['user_name']}, task_count={result['task_count']}")

    # ---- 第2轮对话：设置名字 ----
    print("\n--- 第2轮：设置名字 ---")
    result = agent.invoke(
        {"messages": [HumanMessage(content="我叫张三")]},
        config=config,
    )
    print(f"  AI: {result['messages'][-1].content}")
    print(f"  State: user_name={result['user_name']}, task_count={result['task_count']}")

    # ---- 第3轮对话：验证记忆 ----
    print("\n--- 第3轮：验证记忆 ---")
    result = agent.invoke(
        {"messages": [HumanMessage(content="我叫什么名字？")]},
        config=config,
    )
    print(f"  AI: {result['messages'][-1].content}")
    print(f"  State: user_name={result['user_name']}, task_count={result['task_count']}")

    # ---- 第4轮对话：查询次数 ----
    print("\n--- 第4轮：查询对话次数 ---")
    result = agent.invoke(
        {"messages": [HumanMessage(content="我们对话了几次？")]},
        config=config,
    )
    print(f"  AI: {result['messages'][-1].content}")
    print(f"  State: task_count={result['task_count']}")

    # ---- 查看 Checkpoint 中的历史 ----
    print(f"\n--- Checkpoint 历史 ---")
    checkpoint = memory.get(config)
    if checkpoint:
        # MemorySaver 返回的格式可能是 dict 或 Checkpoint 对象
        if isinstance(checkpoint, dict): 
            #checkpoint 格式 eg: {'thread_id': 'user-001', 'channel_values': {'messages': [...], 'user_name': '张三', 'task_count': 3}}
            values = checkpoint.get("channel_values", checkpoint) #第二个参数是默认值，如果 "channel_values" 不存在，则返回 checkpoint 本身
        else:
            values = getattr(checkpoint, "channel_values", checkpoint)
        print(f"  保存的 State: {values}")
    else:
        print("  无 Checkpoint 数据")


# ========== 5. 多用户隔离演示 ==========
def demo_multi_user():
    """演示多用户会话隔离"""
    print(f"\n{'=' * 60}")
    print("【多用户会话隔离演示】")
    print("=" * 60)

    memory = MemorySaver()
    graph = build_agent()
    agent = graph.compile(checkpointer=memory)

    # 用户 A
    config_a = {"configurable": {"thread_id": "user-A"}}
    agent.invoke(
        {"messages": [HumanMessage(content="我叫Alice")], "user_name": "用户", "task_count": 0},
        config=config_a,
    )

    # 用户 B
    config_b = {"configurable": {"thread_id": "user-B"}}
    agent.invoke(
        {"messages": [HumanMessage(content="我叫Bob")], "user_name": "用户", "task_count": 0},
        config=config_b,
    )

    # 验证隔离
    result_a = agent.invoke(
        {"messages": [HumanMessage(content="我叫什么名字？")]},
        config=config_a,
    )
    result_b = agent.invoke(
        {"messages": [HumanMessage(content="我叫什么名字？")]},
        config=config_b,
    )

    print(f"\n  用户 A 的 AI 回答: {result_a['messages'][-1].content}")
    print(f"  用户 B 的 AI 回答: {result_b['messages'][-1].content}")
    print(f"\n  用户 A 的 user_name: {result_a['user_name']}")
    print(f"  用户 B 的 user_name: {result_b['user_name']}")


# ========== 6. 展示记忆类型 ==========
def show_memory_types():
    """展示 Agent 记忆类型"""
    print("=" * 60)
    print("【Agent 记忆类型】")
    print("=" * 60)
    print("""
    1. 短期记忆（Short-term Memory）
       - 当前会话的消息历史
       - 存储在 State.messages 中
       - 每次对话自动累积
       - 会话结束即丢失（除非 Checkpoint）

    2. 工作记忆（Working Memory）
       - 当前任务的中间状态
       - 存储在 State 的自定义字段中
       - 如：user_name、task_count、current_step
       - 支持 Checkpoint 持久化

    3. 长期记忆（Long-term Memory）
       - 跨会话的知识和偏好
       - 存储在 Redis/数据库中
       - 如：用户画像、历史总结、学习到的知识
       - 需要手动读写

    Checkpoint 机制：
       - MemorySaver：内存存储（开发用）
       - RedisCheckpointer：Redis 存储（生产用）
       - PostgreSQLCheckpointer：PostgreSQL 存储（生产用）
       - 自动保存每次运行的 State
       - 通过 thread_id 隔离不同会话
    """)


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        show_memory_types()
        demo_checkpoint()
        demo_multi_user()

        print(f"\n{'=' * 60}")
        print("[OK] Agent Memory 基础 Demo 完成！")
        print("核心收获：")
        print("  1. Agent 记忆分三种：短期、工作、长期")
        print("  2. MemorySaver 实现内存 Checkpoint")
        print("  3. thread_id 隔离不同用户的会话")
        print("  4. Checkpoint 自动保存/恢复 State")
        print("  5. 生产环境用 RedisCheckpointer")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
