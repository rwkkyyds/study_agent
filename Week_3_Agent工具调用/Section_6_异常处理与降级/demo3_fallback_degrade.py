"""
demo3_fallback_degrade.py - 降级策略与完整容错 Agent

学习目标：
1. Fallback 工具注册（主工具失败 → 切换备用工具）
2. 优雅降级（返回部分结果 + 错误提示）
3. LangGraph 条件路由实现降级分支
4. 完整的三级容错 Agent 工作流

核心思想：即使主工具挂了，也要给用户一个有用的回答，而不是报错。
"""

import logging
import random
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# 1. 定义工具和 Fallback 工具
# ============================================================

# ---- 主工具（可能失败）----

@tool
def web_search(query: str) -> str:
    """网络搜索（模拟不稳定）"""
    if random.random() < 0.6:  # 60% 概率失败
        raise ConnectionError(f"搜索服务暂时不可用")
    return f"搜索结果：找到关于 '{query}' 的 10 条结果"


@tool
def database_query(sql: str) -> str:
    """数据库查询（模拟不稳定）"""
    if random.random() < 0.5:
        raise TimeoutError("数据库连接超时")
    return f"数据库结果：执行 '{sql}' 返回 5 条记录"


# ---- Fallback 工具（备用，更稳定但功能较弱）----

@tool
def cache_search(query: str) -> str:
    """缓存搜索（Fallback - 比较稳定但数据可能过期）"""
    return f"缓存结果：关于 '{query}' 的缓存数据（可能不是最新）"


@tool
def static_faq(topic: str) -> str:
    """静态 FAQ（Fallback - 最后的兜底方案）"""
    faq_data = {
        "天气": "请访问 weather.com 查看天气",
        "股票": "请访问 finance.yahoo.com 查看行情",
        "新闻": "请访问 news.google.com 浏览新闻",
    }
    for key, val in faq_data.items():
        if key in topic:
            return val
    return f"抱歉，暂时无法获取 '{topic}' 的信息，请稍后重试。"


# ============================================================
# 2. Fallback 注册表 - 主工具 → 备用工具映射
# ============================================================

# 这是一个关键设计：每个主工具都有对应的 fallback 链
FALLBACK_CHAIN = {
    "web_search": ["cache_search", "static_faq"],      # 搜索失败 → 缓存 → FAQ
    "database_query": ["cache_search", "static_faq"],   # 数据库失败 → 缓存 → FAQ
}

ALL_TOOLS = {
    "web_search": web_search,
    "database_query": database_query,
    "cache_search": cache_search,
    "static_faq": static_faq,
}


# ============================================================
# 3. 定义 State
# ============================================================

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    error_messages: list[str]
    fallback_used: list[str]     # 记录使用了哪些 fallback
    degradation_level: int       # 降级等级：0=正常, 1=一级降级, 2=二级降级


# ============================================================
# 4. 三级容错工具调用节点
# ============================================================

def resilient_tool_call(state: AgentState) -> dict:  
   
    """
    三级容错工具调用：

    第一级：正常调用主工具
    第二级：主工具失败 → 重试1次
    第三级：重试失败 → 使用 Fallback 工具链
    """
    messages = state["messages"]
    errors = state.get("error_messages", [])
    fallback_used = state.get("fallback_used", [])
    max_level = state.get("degradation_level", 0)

    # 找到最后一条 AI 消息
    last_ai_msg = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            last_ai_msg = msg
            break

    if not last_ai_msg:
        return {}

    results = []

    for tool_call in last_ai_msg.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        # ---- 第一级：正常调用 ----
        logger.info(f"[Level 0] 尝试调用主工具: {tool_name}")
        try:
            tool_func = ALL_TOOLS.get(tool_name)
            if tool_func is None:
                error_msg = f"工具 '{tool_name}' 不存在"
                errors.append(error_msg)
                results.append(ToolMessage(content=f"[ERROR] {error_msg}", tool_call_id=tool_id))
                continue

            result = tool_func.invoke(tool_args)
            logger.info(f"[Level 0] 工具 {tool_name} 成功")
            results.append(ToolMessage(content=result, tool_call_id=tool_id))
            continue

        except Exception as e:
            logger.warning(f"[Level 0] 工具 {tool_name} 失败: {e}")
            errors.append(f"主工具 {tool_name} 失败: {e}")

        # ---- 第二级：重试1次 ----
        logger.info(f"[Level 1] 重试工具: {tool_name}")
        try:
            result = tool_func.invoke(tool_args)
            logger.info(f"[Level 1] 重试成功")
            results.append(ToolMessage(content=result, tool_call_id=tool_id))
            max_level = max(max_level, 1)
            continue

        except Exception as e:
            logger.warning(f"[Level 1] 重试仍然失败: {e}")
            errors.append(f"重试 {tool_name} 失败: {e}")

        # ---- 第三级：Fallback 工具链 ----
        fallbacks = FALLBACK_CHAIN.get(tool_name, [])
        fallback_success = False

        for fb_name in fallbacks:
            logger.info(f"[Level 2] 尝试 Fallback: {fb_name}")
            try:
                fb_func = ALL_TOOLS.get(fb_name)
                if fb_func is None:
                    continue

                # Fallback 工具使用简化的参数
                # 实际项目中可能需要参数转换
                result = fb_func.invoke(tool_args)
                logger.info(f"[Level 2] Fallback {fb_name} 成功")

                fallback_used.append(f"{tool_name} → {fb_name}")
                max_level = max(max_level, 2)

                # 在结果中标注这是降级结果
                degraded_result = f"[降级结果 - 来源: {fb_name}] {result}"
                results.append(ToolMessage(content=degraded_result, tool_call_id=tool_id))
                fallback_success = True
                break

            except Exception as e:
                logger.warning(f"[Level 2] Fallback {fb_name} 也失败: {e}")

        # 所有 Fallback 都失败
        if not fallback_success:
            error_msg = f"工具 {tool_name} 及所有 Fallback 均失败"
            logger.error(error_msg)
            errors.append(error_msg)
            results.append(ToolMessage(
                content=f"[ALL_FAILED] {error_msg}。建议用户稍后重试。",
                tool_call_id=tool_id
            ))
            max_level = 3

    return {
        "messages": results,
        "error_messages": errors,
        "fallback_used": fallback_used,
        "degradation_level": max_level,
    }


# ============================================================
# 5. LangGraph 条件路由：根据降级等级选择不同回复策略
# ============================================================

def should_degrade_response(state: AgentState) -> str:
    """根据降级等级决定走哪条回复路径"""
    level = state.get("degradation_level", 0)
    if level == 0:
        return "normal_response"
    elif level <= 2:
        return "degraded_response"
    else:
        return "failure_response"


def normal_response(state: AgentState) -> dict:
    """正常回复：工具调用成功"""
    logger.info("正常回复路径")
    return {
        "messages": [AIMessage(content="工具调用成功，以下是查询结果。")]
    }


def degraded_response(state: AgentState) -> dict:
    """降级回复：使用了 Fallback，需要告知用户"""
    fallbacks = state.get("fallback_used", [])
    logger.info(f"降级回复路径，使用了 Fallback: {fallbacks}")
    msg = (
        f"主数据源暂时不可用，已使用备用数据源。\n"
        f"注意：结果可能不是最新的。\n"
        f"降级路径: {', '.join(fallbacks) if fallbacks else '未知'}"
    )
    return {"messages": [AIMessage(content=msg)]}


def failure_response(state: AgentState) -> dict:
    """失败回复：所有方案都失败"""
    errors = state.get("error_messages", [])
    logger.error("所有容错方案均失败")
    msg = (
        "非常抱歉，所有数据源均暂时不可用。\n"
        "建议您稍后再试，或联系技术支持。\n"
        f"错误详情: {errors[-1] if errors else '未知错误'}"
    )
    return {"messages": [AIMessage(content=msg)]}


# ============================================================
# 6. 构建完整的容错 Agent 图
# ============================================================

def build_resilient_agent() -> StateGraph:
    """构建带三级容错的 LangGraph Agent"""
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("tool_call", resilient_tool_call)
    graph.add_node("normal_response", normal_response)
    graph.add_node("degraded_response", degraded_response)
    graph.add_node("failure_response", failure_response)

    # 边：工具调用后根据降级等级路由
    graph.add_edge(START, "tool_call")
    graph.add_conditional_edges(
        "tool_call",
        should_degrade_response,
        {
            "normal_response": "normal_response",
            "degraded_response": "degraded_response",
            "failure_response": "failure_response",
        }
    )

    # 所有回复节点都到 END
    graph.add_edge("normal_response", END)
    graph.add_edge("degraded_response", END)
    graph.add_edge("failure_response", END)

    return graph.compile()


# ============================================================
# 7. 演示
# ============================================================

def demo_fallback_chain():
    """演示：Fallback 工具链"""
    print("\n" + "=" * 60)
    print("演示：三级容错 Agent 工作流")
    print("=" * 60)

    agent = build_resilient_agent()

    # 模拟 LLM 决定调用 web_search
    ai_msg = AIMessage(
        content="我来搜索一下",
        tool_calls=[{
            "id": "call_fb_001",
            "name": "web_search",
            "args": {"query": "AI Agent 最新进展"}
        }]
    )

    initial_state = {
        "messages": [HumanMessage(content="AI Agent有什么最新进展"), ai_msg],
        "error_messages": [],
        "fallback_used": [],
        "degradation_level": 0,
    }

    # 运行 Agent
    result = agent.invoke(initial_state)

    # 输出结果
    print(f"\n--- 最终回复 ---")
    for msg in result["messages"]:
        if hasattr(msg, "content"):
            print(f"  {msg.content}")

    print(f"\n--- 运行信息 ---")
    print(f"  错误记录: {result['error_messages']}")
    print(f"  降级路径: {result['fallback_used']}")
    print(f"  降级等级: {result['degradation_level']}")


def demo_multiple_tools_mixed():
    """演示：多个工具调用，混合结果"""
    print("\n" + "=" * 60)
    print("演示：多工具调用 - 混合成功/降级/失败")
    print("=" * 60)

    agent = build_resilient_agent()

    # 模拟同时调用多个工具
    ai_msg = AIMessage(
        content="同时查询多个数据源",
        tool_calls=[
            {"id": "call_mix_001", "name": "web_search", "args": {"query": "Python教程"}},
            {"id": "call_mix_002", "name": "database_query", "args": {"sql": "SELECT * FROM users"}},
        ]
    )

    initial_state = {
        "messages": [HumanMessage(content="帮我查资料"), ai_msg],
        "error_messages": [],
        "fallback_used": [],
        "degradation_level": 0,
    }

    result = agent.invoke(initial_state)

    print(f"\n--- 最终回复 ---")
    for msg in result["messages"]:
        if hasattr(msg, "content"):
            print(f"  {msg.content}")

    print(f"\n--- 运行信息 ---")
    print(f"  错误记录: {result['error_messages']}")
    print(f"  降级路径: {result['fallback_used']}")
    print(f"  降级等级: {result['degradation_level']}")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("demo3: 降级策略与完整容错 Agent")
    print("=" * 60)

    demo_fallback_chain()
    demo_multiple_tools_mixed()

    print("\n" + "=" * 60)
    print("总结：三级容错体系")
    print("=" * 60)
    print("""
    Level 0: 正常调用主工具
        ↓ 失败
    Level 1: 重试1次（给临时故障一个恢复机会）
        ↓ 仍然失败
    Level 2: Fallback 工具链（切换到备用工具）
        ↓ 所有 Fallback 都失败
    Level 3: 优雅失败（告知用户，建议稍后重试）

    关键设计：
    1. Fallback 注册表：主工具 → 备用工具映射
    2. 条件路由：根据降级等级选择不同回复策略
    3. 信息透明：告诉用户结果来自哪个数据源
    """)
