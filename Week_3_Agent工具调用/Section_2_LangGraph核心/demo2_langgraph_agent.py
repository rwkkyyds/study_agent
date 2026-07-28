"""
Demo2: 用 LangGraph 手动构建 ReAct Agent（白盒版）  
ReAct Agent 是一种经典的 Agent 架构，
核心思想是让 Agent 在推理过程中不断循环：思考（Reasoning）→ 行动（Acting）→ 观察（Observation），
直到完成任务。每一步，Agent 都可以选择直接回答用户问题，或者调用工具获取更多信息，再继续推理。
功能：用 StateGraph 显式定义 Agent 的推理循环，而非 create_agent 黑盒
核心：Agent Node → Conditional Edge → Tool Node → 循环
依赖：langchain-openai, langgraph, langchain-core（已有）
前置：先运行 demo1_langgraph_basics.py 理解 StateGraph 基础
"""
import os

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import math
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage 
# ToolMessage 是工具调用的消息类型，包含 tool_calls 字段，LLM 调用工具时返回 ToolMessage，里面有 tool_calls 列表，记录了要调用哪些工具和参数。
# BaseMessage 是所有消息类型的基类，AgentState 中的 messages 是 BaseMessage 列表，可以包含 HumanMessage、AIMessage、ToolMessage 等不同类型的消息。
from langgraph.graph import StateGraph, START, END 
# START 和 END 是 StateGraph 中的特殊节点，分别表示图的开始和结束。
# START 是 Agent 推理的入口，END 是推理完成的出口。
# 在构建 StateGraph 时，我们会从 START 节点出发，定义 Agent Node、Conditional Edge、Tool Node 等节点和边，最终可能会有一些路径通向 END 节点，表示推理结束。
from langgraph.prebuilt import ToolNode 
# ToolNode 是 LangGraph 提供的预构建节点类型，用于执行工具调用。
# 我们在 StateGraph 中添加一个 ToolNode，传入可用工具列表，ToolNode 会根据 LLM 的 tool_calls 自动执行相应工具，并将结果追加到 State.messages 中。
import operator


# ========== 配置 ==========
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 1. 定义工具 ==========
@tool
def calculator(expression: str) -> str:
    """计算数学表达式。支持加减乘除、幂运算、开方等。
    输入示例: '2 + 3 * 4', 'sqrt(16)', '2 ** 10'
    """
    try:
        allowed = {k: v for k, v in math.__dict__.items() if not k.startswith("_")} # 允许 math 模块中的函数（如 sqrt、pow 等）
        result = eval(expression, {"__builtins__": {}}, allowed) # 禁止访问内置函数，防止安全风险
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


@tool
def knowledge_base(query: str) -> str:
    """查询内部知识库，获取技术文档、产品信息等。
    当用户问到技术概念（如 RAG、Agent、ReAct、Milvus、LangGraph）时使用此工具。
    """
    kb = {
        "rag": "RAG（检索增强生成）= 检索外部知识 + LLM 生成回答。核心组件：文档解析、向量化、向量库、检索、重排、生成。",
        "agent": "Agent = LLM（大脑）+ Tools（手脚）+ 推理循环。核心能力：自主决策调用哪个工具、按什么顺序调用。",
        "react": "ReAct = Reasoning + Acting。每一步：Thought（思考）→ Action（行动）→ Observation（观察），循环直到完成任务。",
        "langgraph": "LangGraph 是 LangChain 团队的 Agent 框架，用 StateGraph 显式定义工作流，比 create_agent 更灵活可控。",
        "milvus": "Milvus 是生产级向量数据库，支持十亿级向量检索，Docker 部署，HNSW 索引。",
    }
    query_lower = query.lower()
    results = []
    for key, value in kb.items():
        if key in query_lower:
            results.append(value)
    return "\n".join(results) if results else f"知识库中未找到与 '{query}' 相关的信息。"


@tool
def get_current_time() -> str:
    """获取当前日期和时间。当用户问'现在几点'、'今天几号'时使用。"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


TOOLS = [calculator, knowledge_base, get_current_time]


# ========== 2. 定义 Agent State ==========
# State 是图中流动的数据
# messages 用 Annotated[list, operator.add] 表示"追加"而非"覆盖"
# 这样每个 Node 的返回值会追加到消息列表，而不是替换
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add] 
    #operators.add 表示在 StateGraph 中这个字段的更新方式是追加（而非覆盖）。每次 Agent Node 或 Tool Node 返回新的消息时，都会追加到 messages 列表中，保留完整的消息历史。
    #Annotated 是 Python 3.9+ 的类型注解工具，这里用来标记 messages 是一个列表


# ========== 3. 定义 Agent Node ==========
# Agent Node 的职责：调用 LLM，让 LLM 决定是回答还是调用工具
def agent_node(state: AgentState) -> dict:
    """
    Agent 节点：调用 LLM 决策
    - 如果 LLM 决定调用工具 → 返回 tool_calls（AIMessage 带 tool_calls）
    - 如果 LLM 决定直接回答 → 返回普通 AIMessage（无 tool_calls）
    """
    print("  [Agent Node] 调用 LLM 决策...")

    llm = ChatOpenAI(
        api_key=ZHIPU_API_KEY,
        base_url=ZHIPU_BASE_URL,
        model="glm-4-flash",
        temperature=0,
    )

    # 绑定工具，让 LLM 知道有哪些工具可用
    llm_with_tools = llm.bind_tools(TOOLS)

    # 调用 LLM（传入完整消息历史）
    response = llm_with_tools.invoke(state["messages"])

    # 打印 LLM 的决策
    if response.tool_calls:
        for tc in response.tool_calls:
            print(f"    → LLM 决定调用工具: {tc['name']}({tc['args']})")
    else:
        print(f"    → LLM 决定直接回答")

    # 返回追加到 messages 的新消息
    return {"messages": [response]}
 #eg: {"messages": [AIMessage(content="回答内容",  tool_calls=[{"name": "calculator", "args": {"expression": "2 + 2"}}])]} 
 # 或 {"messages": [AIMessage(content="直接回答内容")]}，
 # StateGraph 会根据 tool_calls 是否存在来判断下一步走哪个分支。


# ========== 4. 定义 Conditional Edge ==========
# 判断是否需要继续调用工具
def should_continue(state: AgentState) -> str:
    """
    条件路由：
    - 最后一条消息有 tool_calls → 去 "tools" 节点执行工具
    - 最后一条消息没有 tool_calls → 结束
    """
    last_message = state["messages"][-1]
    #eg: 最后一条消息是 
    # AIMessage(content="回答内容",  tool_calls=[{"name": "calculator", "args": {"expression": "2 + 2"}}])，
    # 则有工具调用；如果是 AIMessage(content="直接回答内容") 则无工具调用。

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        print("  [Conditional Edge] 有工具调用 → 去执行工具")
        return "tools"
    else:
        print("  [Conditional Edge] 无工具调用 → 结束")
        return "end"


# ========== 5. 构建 LangGraph Agent ==========
def build_langgraph_agent() -> StateGraph:  
    #StateGraph通俗易懂的说就是一个有向图，节点代表 Agent 的不同状态（如思考、行动、观察），
    # 边代表状态之间的转移（如条件判断、工具调用）。通过定义 StateGraph，我们可以清晰地描述 Agent 的推理流程和循环逻辑。
    """
    用 StateGraph 手动构建 ReAct Agent：

    ┌─────────┐
    │  START   │
    └────┬─────┘
         │
    ┌────▼─────┐
    │  agent   │ ← 调用 LLM 决策
    └────┬─────┘
         │
    ┌────▼──────────┐
    │ should_continue│ ← 条件判断
    └──┬─────────┬───┘
       │         │
    "tools"    "end"
       │         │
    ┌──▼───┐     │
    │ tools │     │  ← 执行工具，结果追加到 messages
    └──┬───┘     │
       │         │
       └────┬────┘
            │
       回到 agent（循环）
    """
    graph = StateGraph(AgentState) # 定义 StateGraph，State 类型为 AgentState

    # 添加节点
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))

    # 添加边
    graph.add_edge(START, "agent")                    # START → agent

    # 条件边：agent → should_continue → tools 或 end
    graph.add_conditional_edges(
        "agent",                                       # 从 agent 出发
        should_continue,                               # 路由函数
        {
            "tools": "tools",                          # 有工具调用 → 去 tools
            "end": END                                 # 无工具调用 → 结束
        }
    )

    # tools 执行完后，回到 agent 继续推理
    graph.add_edge("tools", "agent")

    return graph.compile()


# ========== 6. 运行测试 ==========
def run_demo():
    """运行 LangGraph Agent Demo"""
    agent = build_langgraph_agent()

    questions = [
        "计算一下 (15 * 8 + 120) / 4 等于多少？",
        "什么是 LangGraph？它和传统 Agent 有什么区别？",
        "现在几点了？另外帮我算一下 2 的 20 次方是多少？",
    ]

    for i, q in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"问题 {i+1}: {q}")
        print("=" * 60)

        try:
            # invoke 传入初始消息
            result = agent.invoke({"messages": [HumanMessage(content=q)]})

            # 最后一条消息是最终回答
            final_message = result["messages"][-1]
            print(f"\n[最终回答] {final_message.content}")
            

            # 打印完整消息链（调试用）
            print(f"\n--- 消息链 ({len(result['messages'])} 条) ---")
            for j, msg in enumerate(result["messages"]):
                msg_type = type(msg).__name__
                content_preview = msg.content[:80] if msg.content else "(无内容)"
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"  [{j}] {msg_type}: tool_call → {tc['name']}")
                else:
                    print(f"  [{j}] {msg_type}: {content_preview}")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        print("=" * 60)
        print("LangGraph ReAct Agent（白盒版）")
        print("=" * 60)
        print("""
    与 Section 1 的 create_agent 对比：

    create_agent（黑盒）:          LangGraph（白盒）:
      一行代码创建                    手动定义每个节点
      内部自动处理循环                你控制循环逻辑
      难以自定义                      完全可定制

    本 Demo 展示 LangGraph 的手动构建过程：
      1. Agent Node：调用 LLM 决策
      2. Conditional Edge：判断是否调用工具
      3. Tool Node：执行工具
      4. 循环：tools → agent → 判断 → ...
        """)

        run_demo()

        print(f"\n{'=' * 60}")
        print("[OK] LangGraph Agent Demo 完成！")
        print("核心收获：")
        print("  1. LangGraph 用 StateGraph 显式定义 Agent 推理循环")
        print("  2. Agent Node 调用 LLM 决策（回答 or 调用工具）")
        print("  3. Conditional Edge 控制循环（继续调用工具 or 结束）")
        print("  4. Tool Node 执行工具，结果追加到 State.messages")
        print("  5. 比 create_agent 更灵活，可自定义每个环节")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
