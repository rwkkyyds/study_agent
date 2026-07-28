"""
demo1_search_agent.py - 联网搜索 Agent（LangGraph StateGraph 手动构建）

用你学过的 LangGraph 组件：
- StateGraph(AgentState) 定义图
- agent_node 调用 LLM.bind_tools() 决策
- should_continue 条件路由
- ToolNode 执行工具
- add_edge / add_conditional_edges 组装

依赖：langchain-openai, langgraph, langchain-core
"""
import os

import sys, io, operator
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# ========== 配置 ==========
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# ========== 1. 定义搜索工具 ==========
MOCK_DB = {
    "AI Agent": "2024年AI Agent爆发：LangChain发布Agent SDK，OpenAI推出GPTs，AutoGen和CrewAI成为主流。",
    "RAG": "RAG持续进化：混合检索、Rerank重排、语义分块成为标配。Milvus和pgvector是生产级首选。",
    "LLM": "GPT-4o、Claude 4、Gemini 2.0相继发布，多模态能力成为标配。",
}


@tool
def web_search(query: str) -> str:
    """搜索互联网获取最新信息。输入搜索关键词，返回结果摘要。"""
    for key, val in MOCK_DB.items():
        if key.lower() in query.lower():
            return val
    return f"搜索 '{query}' 未找到结果，建议换个关键词。"


@tool
def news_search(query: str) -> str:
    """搜索最新新闻动态。输入关键词，返回新闻摘要。"""
    return f"【新闻】关于 '{query}'：该领域正在快速发展，多家企业已加大投入。"


TOOLS = [web_search, news_search]

# ========== 2. 定义 State ==========
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

# ========== 3. Agent Node ==========
def agent_node(state: AgentState) -> dict:
    """调用 LLM 决策：回答 or 调用工具"""
    llm = ChatOpenAI(
        api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL,
        model="glm-4-flash", temperature=0,
    )
    llm_with_tools = llm.bind_tools(TOOLS)
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# ========== 4. Conditional Edge ==========
def should_continue(state: AgentState) -> str:
    """有 tool_calls → 去执行工具；否则 → 结束"""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "end"

# ========== 5. 构建图 ==========
def build_search_agent():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")
    return graph.compile()

# ========== 6. 演示 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("demo1: 联网搜索 Agent（LangGraph StateGraph）")
    print("=" * 60)

    agent = build_search_agent()

    for q in ["AI Agent 最新进展是什么", "LLM有什么新闻"]:
        print(f"\n--- 问题: {q} ---")
        result = agent.invoke({"messages": [HumanMessage(content=q)]})
        print(f"[最终回答] {result['messages'][-1].content}")
