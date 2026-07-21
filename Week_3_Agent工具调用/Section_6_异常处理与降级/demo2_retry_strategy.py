"""
demo2_retry_strategy.py - 重试策略（指数退避）

学习目标：
1. 掌握 tenacity 库的重试机制 音标 / təˈnæsəti/
2. 理解指数退避（exponential backoff）策略 /eksˈpəʊnənʃəl ˈbækɒf/
3. 按异常类型选择性重试
4. 将重试集成到 LangGraph Agent 中

为什么需要重试？
很多工具调用失败是临时性的（网络抖动、API限流、服务暂时不可用），
直接放弃太可惜，自动重试几次可能就成功了。
但不能无限重试，也不能立即重试（可能把对方打爆）。
"""

import logging
import random
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages # 用于在 StateGraph 中标记消息列表
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

# tenacity 是 Python 生产级重试库
from tenacity import (
    retry,
    stop_after_attempt,      # 最大重试次数
    wait_exponential,        # 指数退避等待
    retry_if_exception_type, # 只对特定异常重试
    before_sleep_log,        # 每次重试前记录日志
)

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s" #asctime: 时间戳, levelname: 日志级别, message: 日志内容
)
logger = logging.getLogger(__name__) #创建一个 logger 对象，__name__ 是当前模块的名字，这样日志会显示模块名，方便排查问题


# ============================================================
# 1. 模拟一个"不稳定的"API 工具
# ============================================================

class FlakyAPI:
    """
    模拟一个不稳定的 API：
    - 前几次调用可能失败（模拟限流、网络抖动）
    - 失败次数达到阈值后开始成功
    """
    def __init__(self, fail_count: int = 2):
        self.call_count = 0
        self.fail_count = fail_count  # 前 N 次调用会失败

    def call(self, query: str) -> str:
        self.call_count += 1
        current = self.call_count

        if current <= self.fail_count:
            # 模拟不同的失败原因
            if current % 2 == 1:
                raise ConnectionError(f"API 429 限流 (第{current}次调用)")
            else:
                raise TimeoutError(f"API 超时 (第{current}次调用)")

        return f"API 返回结果：'{query}' 的数据 (第{current}次调用成功)"


# 创建实例：前2次会失败，第3次成功
flaky_api = FlakyAPI(fail_count=2)


# ============================================================
# 2. 用 tenacity 包装重试逻辑
# ============================================================

# ---- 方式1：装饰器方式（最常用）----
# ⚠️ @retry 装饰器的工作流程：
# 1. 运行函数内代码
# 2. 如果抛出异常，装饰器会捕获它
# 3. 检查异常是否在 retry_if_exception_type 中
# 4. 如果是 → 记录日志 → 等待 → 重试
# 5. 如果不是 → 直接抛出异常（不重试）
@retry(
    # 只对这些异常进行重试（装饰器会拦截这些异常）
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    # 最多重试 3 次（包括首次调用）
    stop=stop_after_attempt(3),
    # 指数退避：第1次等1秒，第2次等2秒，第3次等4秒...
    # 参数：min=最小等待秒数, max=最大等待秒数, multiplier=倍数(默认2)
    wait=wait_exponential(min=1, max=10, multiplier=2),
    # 每次重试前记录日志（这就是你看到的 [WARNING] 日志来源）
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def call_api_with_retry(query: str) -> str:
    """带重试的 API 调用
    
    关键：这个函数本身不处理异常，
    而是让 @retry 装饰器来处理抛出的异常。
    """
    logger.info(f"尝试调用 API: {query}")
    result = flaky_api.call(query)  # ← 可能 raise ConnectionError，被装饰器捕获
    return result


# ---- 方式2：手动重试（更灵活，适合需要自定义逻辑的场景）----
def call_api_manual_retry(query: str, max_retries: int = 3) -> tuple[str, int]:
    """
    手动实现重试逻辑，返回 (结果, 实际重试次数)

    手动方式的好处：
    - 可以在每次重试时修改参数
    - 可以记录每次重试的详细信息
    - 可以实现更复杂的重试策略
    """
    last_error = None
    retries = 0

    for attempt in range(max_retries):
        try:
            logger.info(f"第 {attempt + 1} 次尝试调用 API")
            result = flaky_api.call(query)
            return result, retries

        except (ConnectionError, TimeoutError) as e:
            last_error = e
            retries += 1

            # 指数退避 + 随机抖动（jitter）
            # jitter 避免多个客户端同时重试（雷群效应）
            wait_time = (2 ** attempt) + random.uniform(0, 1) #uniform(0, 1) 生成一个0到1之间的随机浮点数
            logger.warning(
                f"调用失败 ({type(e).__name__}: {e})，"
                f"等待 {wait_time:.1f} 秒后重试..."
            )
            import time
            time.sleep(wait_time)

        except Exception as e:
            # 非临时性错误，不重试
            logger.error(f"不可恢复的错误: {type(e).__name__}: {e}")
            raise

    raise last_error


# ============================================================
# 3. 将重试集成到 LangGraph Agent
# ============================================================

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    error_messages: list[str]
    retry_info: list[str]   # 记录重试信息


def agent_with_retry(state: AgentState) -> dict:
    """
    带重试的工具调用节点。

    流程：
    1. 从 AI 消息中提取 tool_calls
    2. 对每个工具调用执行重试逻辑
    3. 记录重试信息
    """
    messages = state["messages"]
    errors = state.get("error_messages", [])
    retry_info = state.get("retry_info", [])

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

        try:
            logger.info(f"[Agent] 调用工具: {tool_name}")

            # 使用重试包装的调用
            result, retries = call_api_manual_retry(
                tool_args.get("query", ""),
                max_retries=3
            )

            if retries > 0:
                info = f"工具 {tool_name} 在第 {retries + 1} 次重试后成功"
                retry_info.append(info)
                logger.info(info)

            results.append(ToolMessage(content=result, tool_call_id=tool_id))

        except (ConnectionError, TimeoutError) as e:
            # 重试全部用完仍然失败
            error_msg = f"工具 {tool_name} 重试耗尽后仍失败: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            results.append(ToolMessage(
                content=f"[RETRY_EXHAUSTED] {error_msg}",
                tool_call_id=tool_id
            ))

        except Exception as e:
            error_msg = f"工具 {tool_name} 不可恢复错误: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            results.append(ToolMessage(
                content=f"[ERROR] {error_msg}",
                tool_call_id=tool_id
            ))

    return {
        "messages": results,
        "error_messages": errors,
        "retry_info": retry_info
    }


# ============================================================
# 4. 演示
# ============================================================

def demo_tenacity_basics():
    """演示：tenacity 装饰器方式重试"""
    print("\n" + "=" * 60)
    print("场景1：tenacity 装饰器重试（前2次失败，第3次成功）")
    print("=" * 60)

    # 重置 API 状态
    global flaky_api  
    flaky_api = FlakyAPI(fail_count=2) #有global才是全局修改不然就只是局部变量创建

    try:
        result = call_api_with_retry("查询天气")
        print(f"\n最终结果: {result}")
    except Exception as e:
        print(f"\n最终失败: {e}")


def demo_manual_retry():
    """演示：手动重试"""
    print("\n" + "=" * 60)
    print("场景2：手动重试（前2次失败，第3次成功）")
    print("=" * 60)

    global flaky_api
    flaky_api = FlakyAPI(fail_count=2)

    result, retries = call_api_manual_retry("查询股价", max_retries=3)
    print(f"\n最终结果: {result}")
    print(f"重试次数: {retries}")


def demo_retry_exhausted():
    """演示：重试次数用完仍然失败"""
    print("\n" + "=" * 60)
    print("场景3：重试耗尽（5次失败，只允许重试3次）")
    print("=" * 60)

    global flaky_api
    flaky_api = FlakyAPI(fail_count=5)  # 会连续失败5次

    try:
        result, retries = call_api_manual_retry("不可能成功的查询", max_retries=3)
        print(f"\n最终结果: {result}")
    except Exception as e:
        print(f"\n重试3次后仍然失败: {type(e).__name__}: {e}")


def demo_agent_retry():
    """演示：LangGraph Agent 集成重试"""
    print("\n" + "=" * 60)
    print("场景4：LangGraph Agent 集成重试")
    print("=" * 60)

    # 重置为只失败1次
    global flaky_api
    flaky_api = FlakyAPI(fail_count=1)

    ai_msg = AIMessage(
        content="我来查询一下",
        tool_calls=[{
            "id": "call_retry_001",
            "name": "call_api",
            "args": {"query": "今日新闻"}
        }]
    )

    state = {
        "messages": [HumanMessage(content="今天有什么新闻"), ai_msg],
        "error_messages": [],
        "retry_info": []
    }

    result = agent_with_retry(state)
    print(f"\n工具结果: {result['messages'][0].content}")
    print(f"错误记录: {result['error_messages']}")
    print(f"重试记录: {result['retry_info']}")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("demo2: 重试策略（指数退避）")
    print("=" * 60)

    demo_tenacity_basics()
    demo_manual_retry()
    demo_retry_exhausted()
    demo_agent_retry()

    print("\n" + "=" * 60)
    print("总结：重试策略核心要点")
    print("=" * 60)
    print("""
    1. 指数退避：第1次等1s，第2次等2s，第3次等4s...
       → 避免频繁重试把服务打爆

    2. 随机抖动（Jitter）：在指数退避基础上加随机时间
       → 避免多个客户端同时重试（雷群效应）

    3. 选择性重试：只对临时性异常重试（Timeout、429）
       → 永久性错误（400、403）重试也没用

    4. 最大重试次数：通常 3-5 次
       → 不可能无限重试

    5. 重试信息要记录：方便排查问题
    """)
