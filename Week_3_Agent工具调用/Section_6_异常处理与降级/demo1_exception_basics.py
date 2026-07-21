"""
demo1_exception_basics.py - Agent 工具调用异常捕获基础

学习目标：
1. 理解工具调用中常见的异常类型
2. 用 try-except 捕获工具执行错误
3. 将错误信息反馈给 LLM 让它自动修正

核心思想：Agent 调用工具时不能因为一个工具报错就整个崩掉，
         而是捕获错误、记录日志、把错误信息返回给 LLM 让它想办法。
"""

import logging
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
# 1. 定义几个"有问题"的工具，模拟真实场景中的异常
# ============================================================

@tool
def search_web(query: str) -> str:
    """模拟网络搜索工具 - 有时会超时"""
    # 模拟：某些查询会触发"超时"
    if "error" in query.lower():
        raise TimeoutError(f"搜索 '{query}' 超时：网络连接失败")
    return f"搜索结果：关于 '{query}' 的前3条结果"


@tool
def read_database(sql: str) -> str:
    """模拟数据库查询工具 - 可能返回格式错误"""
    # 模拟：某些 SQL 会触发"格式错误"
    if "invalid" in sql.lower():
        # 返回一个 LLM 无法正常解析的格式
        return "ERROR: malformed response - 数据库连接池耗尽"
    return f"数据库查询结果：执行 '{sql}' 返回 5 条记录"


@tool
def call_api(endpoint: str) -> str:
    """模拟 API 调用工具 - 可能返回 429 限流"""
    if "rate" in endpoint.lower():
        raise ConnectionError(f"API {endpoint} 返回 429 Too Many Requests")
    return f"API 响应：{endpoint} 返回成功"


# ============================================================
# 2. 工具集合 - 用于 Agent 调用
# ============================================================
tools = [search_web, read_database, call_api]
tools_by_name = {t.name: t for t in tools}


# ============================================================
# 3. 定义 State - 关键：增加 error_messages 字段
# ============================================================

class AgentState(TypedDict):
    """Agent 状态，包含消息历史和错误记录"""
    messages: Annotated[list, add_messages] #add_messages 是一个特殊的标记，表示这个字段会被 add_messages 函数自动更新
    error_messages: list[str]   # 记录工具调用中的错误
    retry_count: int            # 当前重试次数


# ============================================================
# 4. 安全工具调用节点 - 核心：try-except 包裹工具执行
# ============================================================

def safe_tool_call(state: AgentState) -> dict:
    """
    安全地调用工具。

    关键逻辑：
    1. 从最后一条 AI 消息中提取工具调用请求
    2. 用 try-except 包裹工具执行
    3. 如果成功 → 返回正常结果
    4. 如果失败 → 返回错误信息，让 LLM 知道发生了什么
    """
    messages = state["messages"]
    errors = state.get("error_messages", [])

    # 找到最后一条 AI 消息（应该包含 tool_calls）
    last_ai_msg = None
    for msg in reversed(messages): #reversed(messages) 是一个内置函数，
        #它会返回一个反向迭代器，用于从列表的最后一个元素开始向前遍历。
        # 这里的目的是从消息列表中找到最后一条 AI 消息，因为通常工具调用请求是由 AI 消息发起的。
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            last_ai_msg = msg
            break

    if not last_ai_msg:
        logger.warning("没有找到包含 tool_calls 的 AI 消息")
        return {}

    results = []
    for tool_call in last_ai_msg.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        logger.info(f"调用工具: {tool_name}({tool_args})")

        try:
            # ====== 核心：try-except 包裹工具执行 ======
            tool_func = tools_by_name.get(tool_name) 
            if tool_func is None:
                # 工具不存在（LLM 幻觉）
                error_msg = f"工具 '{tool_name}' 不存在，可用工具：{list(tools_by_name.keys())}"
                logger.error(error_msg)
                errors.append(error_msg)
                results.append(ToolMessage(
                    content=f"[ERROR] {error_msg}",
                    tool_call_id=tool_id
                ))
                continue

            # 正常调用工具
            result = tool_func.invoke(tool_args)
            logger.info(f"工具 {tool_name} 执行成功: {result[:50]}...")
            results.append(ToolMessage(
                content=result,
                tool_call_id=tool_id
            ))

        except TimeoutError as e:
            # 网络超时 - 可重试
            error_msg = f"工具 {tool_name} 超时: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            results.append(ToolMessage(
                content=f"[TIMEOUT] {error_msg}",
                tool_call_id=tool_id
            ))

        except ConnectionError as e:
            # 连接错误 / 限流 - 可重试
            error_msg = f"工具 {tool_name} 连接失败: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            results.append(ToolMessage(
                content=f"[CONNECTION_ERROR] {error_msg}",
                tool_call_id=tool_id
            ))

        except Exception as e:
            # 兜底：捕获所有其他异常
            error_msg = f"工具 {tool_name} 发生未知错误: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            results.append(ToolMessage(
                content=f"[UNKNOWN_ERROR] {error_msg}",
                tool_call_id=tool_id
            ))

    return {
        "messages": results,
        "error_messages": errors
    }


# ============================================================
# 5. 演示：模拟 LLM 决策（不依赖真实 LLM）
# ============================================================

def demo_normal_call():
    """演示：正常工具调用"""
    print("\n" + "=" * 60)
    print("场景1：正常工具调用")
    print("=" * 60)

    # 模拟 LLM 决定调用 search_web
    ai_msg = AIMessage(
        content="我来搜索一下",
        tool_calls=[{
            "id": "call_001",
            "name": "search_web",
            "args": {"query": "LangChain教程"}
        }]
    )

    state = {
        "messages": [HumanMessage(content="帮我搜搜LangChain教程"), ai_msg],
        "error_messages": [],
        "retry_count": 0
    }

    result = safe_tool_call(state)
    print(f"结果: {result['messages'][0].content}")
    print(f"错误记录: {result['error_messages']}")


def demo_timeout_call():
    """演示：工具超时异常"""
    print("\n" + "=" * 60)
    print("场景2：工具超时（触发 TimeoutError）")
    print("=" * 60)

    ai_msg = AIMessage(
        content="我来搜索一下",
        tool_calls=[{
            "id": "call_002",
            "name": "search_web",
            "args": {"query": "error test query"}
        }]
    )

    state = {
        "messages": [HumanMessage(content="搜索一些内容"), ai_msg],
        "error_messages": [],
        "retry_count": 0
    }

    result = safe_tool_call(state) #result格式是一个字典，包含两个键： "messages" 和 "error_messages"。
    print(f"结果: {result['messages'][0].content}")
    print(f"错误记录: {result['error_messages']}")


def demo_nonexistent_tool():
    """演示：LLM 幻觉调用不存在的工具"""
    print("\n" + "=" * 60)
    print("场景3：调用不存在的工具（LLM 幻觉）")
    print("=" * 60)

    ai_msg = AIMessage(
        content="我来调用一个工具",
        tool_calls=[{
            "id": "call_003",
            "name": "magic_tool",  # 不存在的工具
            "args": {"input": "do something"}
        }]
    )

    state = {
        "messages": [HumanMessage(content="帮我做点什么"), ai_msg],
        "error_messages": [],
        "retry_count": 0
    }

    result = safe_tool_call(state)
    print(f"结果: {result['messages'][0].content}")
    print(f"错误记录: {result['error_messages']}")


def demo_multiple_calls_with_one_failure():
    """演示：多个工具调用，其中一个失败"""
    print("\n" + "=" * 60)
    print("场景4：多个工具调用，一个成功一个失败")
    print("=" * 60)

    ai_msg = AIMessage(
        content="我同时搜索和查询数据库",
        tool_calls=[
            {
                "id": "call_004a",
                "name": "search_web",
                "args": {"query": "Python教程"}  # 正常
            },
            {
                "id": "call_004b",
                "name": "read_database",
                "args": {"sql": "SELECT * FROM invalid_table"}  # 会失败
            }
        ]
    )

    state = {
        "messages": [HumanMessage(content="帮我查资料"), ai_msg],
        "error_messages": [],
        "retry_count": 0
    }

    result = safe_tool_call(state)  
    for msg in result["messages"]:
        print(f"结果: {msg.content}")
    print(f"错误记录: {result['error_messages']}")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("demo1: Agent 工具调用异常捕获基础")
    print("=" * 60)

    demo_normal_call()
    demo_timeout_call()
    demo_nonexistent_tool()
    demo_multiple_calls_with_one_failure()

    print("\n" + "=" * 60)
    print("总结：异常捕获的核心模式")
    print("=" * 60)
    print("""
    try:
        result = tool.invoke(args)          # 调用工具
    except TimeoutError:
        # 网络超时 → 记录错误，返回超时提示给 LLM
    except ConnectionError:
        # 连接/限流 → 记录错误，返回连接错误给 LLM
    except Exception as e:
        # 兜底    → 记录错误，返回未知错误给 LLM

    关键：错误信息要返回给 LLM，让它决定下一步怎么做！
    """)
