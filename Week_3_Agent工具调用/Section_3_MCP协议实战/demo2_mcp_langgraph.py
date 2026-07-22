"""
Demo2: MCP + LangGraph 集成（Client 连接 Server → Agent 使用 MCP 工具）
功能：启动 MCP Server → Client 发现工具 → 转换为 LangChain Tool → LangGraph Agent 调用
核心：MCP 工具与 LangGraph Agent 的无缝集成
依赖：langchain-mcp-adapters, langgraph, langchain-openai（已有）
前置：先运行 demo1_mcp_server.py 理解 MCP Server
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import asyncio
import os
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
import operator


# ========== 配置 ==========
ZHIPU_API_KEY = "70041ddde9824461bfb02fac3f469fc3.pDZCoxOgkovIx1vT"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# MCP Server 路径（demo1 的 Server）
MCP_SERVER_PATH = os.path.join(os.path.dirname(__file__), "demo1_mcp_server.py")


# ========== 1. Agent State（与 Section 2 相同） ==========
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


# ========== 2. Agent Node（含重试） ==========
def create_agent_node(llm_with_tools, max_retries: int = 3):
    """创建 Agent Node（闭包，捕获 llm_with_tools，含网络重试）"""
    def agent_node(state: AgentState) -> dict:
        print("  [Agent Node] 调用 LLM 决策...")
        for attempt in range(max_retries):
            try:
                response = llm_with_tools.invoke(state["messages"])
                if response.tool_calls:
                    for tc in response.tool_calls:
                        print(f"    → LLM 决定调用 MCP 工具: {tc['name']}({tc['args']})")
                else:
                    print(f"    → LLM 决定直接回答")
                return {"messages": [response]}
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"    → 网络错误，重试 {attempt + 1}/{max_retries}...")
                    import time
                    time.sleep(2)
                else:
                    raise
    return agent_node


# ========== 3. Conditional Edge ==========
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        print("  [Conditional Edge] 有工具调用 → 去执行 MCP 工具")
        return "tools"
    print("  [Conditional Edge] 无工具调用 → 结束")
    return "end"


# ========== 4. 构建 LangGraph Agent ==========
def build_agent(llm_with_tools, tools):
    """构建 LangGraph Agent"""
    graph = StateGraph(AgentState)

    graph.add_node("agent", create_agent_node(llm_with_tools))
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "end": END
    })
    graph.add_edge("tools", "agent") 

    return graph.compile()


# ========== 5. 主流程 ==========
async def main():
    print("=" * 60)
    print("MCP + LangGraph 集成 Demo")
    print("=" * 60)
    print(f"""
    流程：
    1. 启动 MCP Server（demo1_mcp_server.py 作为子进程）
    2. MCP Client 连接 Server，发现工具
    3. 将 MCP 工具转换为 LangChain Tool
    4. LangGraph Agent 使用 MCP 工具

    架构：
    ┌──────────────┐    stdio     ┌──────────────┐
    │  MCP Client   │ ←──JSON──→ │  MCP Server   │
    │  (本脚本)      │   -RPC     │  (demo1)      │
    └──────┬───────┘             └──────┬───────┘
           │                            │
           ▼                            ▼
    LangGraph Agent              calculator
    (LLM 决策)                   get_weather
                                 get_time
    """)

    # 连接 MCP Server
    # MultiServerMCPClient 可以同时连接多个 MCP Server
    # connections dict 的 key 是 server 名称，value 是连接配置
    # 注意：langchain-mcp-adapters 0.3.0 不支持 async with，直接实例化即可
    mcp_client = MultiServerMCPClient(
        connections={
            "calculator": { 
                "transport": "stdio", # 使用 stdio 连接 MCP Server
                "command": sys.executable,  # python 解释器路径
                "args": [MCP_SERVER_PATH],  # Server 脚本路径
            }
        }
    )

    # ========== Step 1: 发现 MCP 工具 ==========
    print("=" * 60)
    print("【Step 1: 发现 MCP Server 暴露的工具】")
    print("=" * 60)

    mcp_tools = await mcp_client.get_tools() 
    # 获取 MCP Server 暴露的工具列表，转换为 LangChain Tool 对象
    # LangChain Tool 对象包含 name, description, args_schema（参数定义）等信息
    print(f"\n  发现 {len(mcp_tools)} 个 MCP 工具:")
    for t in mcp_tools:
        print(f"    - {t.name}: {t.description}")

    # ========== Step 2: 创建 LLM ==========
    llm = ChatOpenAI(
        api_key=ZHIPU_API_KEY,
        base_url=ZHIPU_BASE_URL,
        model="glm-4-flash",
        temperature=0,
    )

    # 绑定 MCP 工具到 LLM
    llm_with_tools = llm.bind_tools(mcp_tools)

    # ========== Step 3: 构建 LangGraph Agent ==========
    agent = build_agent(llm_with_tools, mcp_tools)

    # ========== Step 4: 测试 Agent ==========
    questions = [
        "计算一下 (100 - 37) * 2 等于多少？",
        "北京今天天气怎么样？",
        "现在几点了？另外帮我算一下 3 的 10 次方。",
    ]

    for i, q in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"问题 {i+1}: {q}")
        print("=" * 60)

        try:
            result = await agent.ainvoke({"messages": [HumanMessage(content=q)]})
            final_message = result["messages"][-1]
            print(f"\n[最终回答] {final_message.content}")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print("[OK] MCP + LangGraph 集成 Demo 完成！")
    print("核心收获：")
    print("  1. MCP Server 是独立进程，通过 stdio 与 Client 通信")
    print("  2. MultiServerMCPClient 可连接多个 MCP Server")
    print("  3. mcp_client.get_tools() 返回 LangChain 兼容的工具列表")
    print("  4. MCP 工具可直接绑定到 LLM 和 LangGraph Agent")
    print("  5. 工具实现与 Agent 代码完全解耦")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
