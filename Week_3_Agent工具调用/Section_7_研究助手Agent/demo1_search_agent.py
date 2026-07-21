"""
demo1_search_agent.py - 鑱旂綉鎼滅储 Agent锛圠angGraph StateGraph 鎵嬪姩鏋勫缓锛?
鐢ㄤ綘瀛﹁繃鐨?LangGraph 缁勪欢锛?- StateGraph(AgentState) 瀹氫箟鍥?- agent_node 璋冪敤 LLM.bind_tools() 鍐崇瓥
- should_continue 鏉′欢璺敱
- ToolNode 鎵ц宸ュ叿
- add_edge / add_conditional_edges 缁勮

渚濊禆锛歭angchain-openai, langgraph, langchain-core
"""

import sys, io, operator
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# ========== 閰嶇疆 ==========
ZHIPU_API_KEY = __import__("os").environ.get("ZHIPU_API_KEY")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# ========== 1. 瀹氫箟鎼滅储宸ュ叿 ==========
MOCK_DB = {
    "AI Agent": "2024骞碅I Agent鐖嗗彂锛歀angChain鍙戝竷Agent SDK锛孫penAI鎺ㄥ嚭GPTs锛孉utoGen鍜孋rewAI鎴愪负涓绘祦銆?,
    "RAG": "RAG鎸佺画杩涘寲锛氭贩鍚堟绱€丷erank閲嶆帓銆佽涔夊垎鍧楁垚涓烘爣閰嶃€侻ilvus鍜宲gvector鏄敓浜х骇棣栭€夈€?,
    "LLM": "GPT-4o銆丆laude 4銆丟emini 2.0鐩哥户鍙戝竷锛屽妯℃€佽兘鍔涙垚涓烘爣閰嶃€?,
}


@tool
def web_search(query: str) -> str:
    """鎼滅储浜掕仈缃戣幏鍙栨渶鏂颁俊鎭€傝緭鍏ユ悳绱㈠叧閿瘝锛岃繑鍥炵粨鏋滄憳瑕併€?""
    for key, val in MOCK_DB.items():
        if key.lower() in query.lower():
            return val
    return f"鎼滅储 '{query}' 鏈壘鍒扮粨鏋滐紝寤鸿鎹釜鍏抽敭璇嶃€?


@tool
def news_search(query: str) -> str:
    """鎼滅储鏈€鏂版柊闂诲姩鎬併€傝緭鍏ュ叧閿瘝锛岃繑鍥炴柊闂绘憳瑕併€?""
    return f"銆愭柊闂汇€戝叧浜?'{query}'锛氳棰嗗煙姝ｅ湪蹇€熷彂灞曪紝澶氬浼佷笟宸插姞澶ф姇鍏ャ€?


TOOLS = [web_search, news_search]

# ========== 2. 瀹氫箟 State ==========
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

# ========== 3. Agent Node ==========
def agent_node(state: AgentState) -> dict:
    """璋冪敤 LLM 鍐崇瓥锛氬洖绛?or 璋冪敤宸ュ叿"""
    llm = ChatOpenAI(
        api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL,
        model="glm-4-flash", temperature=0,
    )
    llm_with_tools = llm.bind_tools(TOOLS)
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# ========== 4. Conditional Edge ==========
def should_continue(state: AgentState) -> str:
    """鏈?tool_calls 鈫?鍘绘墽琛屽伐鍏凤紱鍚﹀垯 鈫?缁撴潫"""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "end"

# ========== 5. 鏋勫缓鍥?==========
def build_search_agent():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")
    return graph.compile()

# ========== 6. 婕旂ず ==========
if __name__ == "__main__":
    print("=" * 60)
    print("demo1: 鑱旂綉鎼滅储 Agent锛圠angGraph StateGraph锛?)
    print("=" * 60)

    agent = build_search_agent()

    for q in ["AI Agent 鏈€鏂拌繘灞曟槸浠€涔?, "LLM鏈変粈涔堟柊闂?]:
        print(f"\n--- 闂: {q} ---")
        result = agent.invoke({"messages": [HumanMessage(content=q)]})
        print(f"[鏈€缁堝洖绛擼 {result['messages'][-1].content}")

