"""
Demo2: MCP + LangGraph 闆嗘垚锛圕lient 杩炴帴 Server 鈫?Agent 浣跨敤 MCP 宸ュ叿锛?鍔熻兘锛氬惎鍔?MCP Server 鈫?Client 鍙戠幇宸ュ叿 鈫?杞崲涓?LangChain Tool 鈫?LangGraph Agent 璋冪敤
鏍稿績锛歁CP 宸ュ叿涓?LangGraph Agent 鐨勬棤缂濋泦鎴?渚濊禆锛歭angchain-mcp-adapters, langgraph, langchain-openai锛堝凡鏈夛級
鍓嶇疆锛氬厛杩愯 demo1_mcp_server.py 鐞嗚В MCP Server
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


# ========== 閰嶇疆 ==========
ZHIPU_API_KEY = __import__("os").environ.get("ZHIPU_API_KEY")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# MCP Server 璺緞锛坉emo1 鐨?Server锛?MCP_SERVER_PATH = os.path.join(os.path.dirname(__file__), "demo1_mcp_server.py")


# ========== 1. Agent State锛堜笌 Section 2 鐩稿悓锛?==========
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


# ========== 2. Agent Node锛堝惈閲嶈瘯锛?==========
def create_agent_node(llm_with_tools, max_retries: int = 3):
    """鍒涘缓 Agent Node锛堥棴鍖咃紝鎹曡幏 llm_with_tools锛屽惈缃戠粶閲嶈瘯锛?""
    def agent_node(state: AgentState) -> dict:
        print("  [Agent Node] 璋冪敤 LLM 鍐崇瓥...")
        for attempt in range(max_retries):
            try:
                response = llm_with_tools.invoke(state["messages"])
                if response.tool_calls:
                    for tc in response.tool_calls:
                        print(f"    鈫?LLM 鍐冲畾璋冪敤 MCP 宸ュ叿: {tc['name']}({tc['args']})")
                else:
                    print(f"    鈫?LLM 鍐冲畾鐩存帴鍥炵瓟")
                return {"messages": [response]}
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"    鈫?缃戠粶閿欒锛岄噸璇?{attempt + 1}/{max_retries}...")
                    import time
                    time.sleep(2)
                else:
                    raise
    return agent_node


# ========== 3. Conditional Edge ==========
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        print("  [Conditional Edge] 鏈夊伐鍏疯皟鐢?鈫?鍘绘墽琛?MCP 宸ュ叿")
        return "tools"
    print("  [Conditional Edge] 鏃犲伐鍏疯皟鐢?鈫?缁撴潫")
    return "end"


# ========== 4. 鏋勫缓 LangGraph Agent ==========
def build_agent(llm_with_tools, tools):
    """鏋勫缓 LangGraph Agent"""
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


# ========== 5. 涓绘祦绋?==========
async def main():
    print("=" * 60)
    print("MCP + LangGraph 闆嗘垚 Demo")
    print("=" * 60)
    print(f"""
    娴佺▼锛?    1. 鍚姩 MCP Server锛坉emo1_mcp_server.py 浣滀负瀛愯繘绋嬶級
    2. MCP Client 杩炴帴 Server锛屽彂鐜板伐鍏?    3. 灏?MCP 宸ュ叿杞崲涓?LangChain Tool
    4. LangGraph Agent 浣跨敤 MCP 宸ュ叿

    鏋舵瀯锛?    鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?   stdio     鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?    鈹? MCP Client   鈹?鈫愨攢鈹€JSON鈹€鈹€鈫?鈹? MCP Server   鈹?    鈹? (鏈剼鏈?      鈹?  -RPC     鈹? (demo1)      鈹?    鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹?            鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹?           鈹?                           鈹?           鈻?                           鈻?    LangGraph Agent              calculator
    (LLM 鍐崇瓥)                   get_weather
                                 get_time
    """)

    # 杩炴帴 MCP Server
    # MultiServerMCPClient 鍙互鍚屾椂杩炴帴澶氫釜 MCP Server
    # connections dict 鐨?key 鏄?server 鍚嶇О锛寁alue 鏄繛鎺ラ厤缃?    # 娉ㄦ剰锛歭angchain-mcp-adapters 0.3.0 涓嶆敮鎸?async with锛岀洿鎺ュ疄渚嬪寲鍗冲彲
    mcp_client = MultiServerMCPClient(
        connections={
            "calculator": { 
                "transport": "stdio", # 浣跨敤 stdio 杩炴帴 MCP Server
                "command": sys.executable,  # python 瑙ｉ噴鍣ㄨ矾寰?                "args": [MCP_SERVER_PATH],  # Server 鑴氭湰璺緞
            }
        }
    )

    # ========== Step 1: 鍙戠幇 MCP 宸ュ叿 ==========
    print("=" * 60)
    print("銆怱tep 1: 鍙戠幇 MCP Server 鏆撮湶鐨勫伐鍏枫€?)
    print("=" * 60)

    mcp_tools = await mcp_client.get_tools() 
    # 鑾峰彇 MCP Server 鏆撮湶鐨勫伐鍏峰垪琛紝杞崲涓?LangChain Tool 瀵硅薄
    # LangChain Tool 瀵硅薄鍖呭惈 name, description, args_schema锛堝弬鏁板畾涔夛級绛変俊鎭?    print(f"\n  鍙戠幇 {len(mcp_tools)} 涓?MCP 宸ュ叿:")
    for t in mcp_tools:
        print(f"    - {t.name}: {t.description}")

    # ========== Step 2: 鍒涘缓 LLM ==========
    llm = ChatOpenAI(
        api_key=ZHIPU_API_KEY,
        base_url=ZHIPU_BASE_URL,
        model="glm-4-flash",
        temperature=0,
    )

    # 缁戝畾 MCP 宸ュ叿鍒?LLM
    llm_with_tools = llm.bind_tools(mcp_tools)

    # ========== Step 3: 鏋勫缓 LangGraph Agent ==========
    agent = build_agent(llm_with_tools, mcp_tools)

    # ========== Step 4: 娴嬭瘯 Agent ==========
    questions = [
        "璁＄畻涓€涓?(100 - 37) * 2 绛変簬澶氬皯锛?,
        "鍖椾含浠婂ぉ澶╂皵鎬庝箞鏍凤紵",
        "鐜板湪鍑犵偣浜嗭紵鍙﹀甯垜绠椾竴涓?3 鐨?10 娆℃柟銆?,
    ]

    for i, q in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"闂 {i+1}: {q}")
        print("=" * 60)

        try:
            result = await agent.ainvoke({"messages": [HumanMessage(content=q)]})
            final_message = result["messages"][-1]
            print(f"\n[鏈€缁堝洖绛擼 {final_message.content}")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print("[OK] MCP + LangGraph 闆嗘垚 Demo 瀹屾垚锛?)
    print("鏍稿績鏀惰幏锛?)
    print("  1. MCP Server 鏄嫭绔嬭繘绋嬶紝閫氳繃 stdio 涓?Client 閫氫俊")
    print("  2. MultiServerMCPClient 鍙繛鎺ュ涓?MCP Server")
    print("  3. mcp_client.get_tools() 杩斿洖 LangChain 鍏煎鐨勫伐鍏峰垪琛?)
    print("  4. MCP 宸ュ叿鍙洿鎺ョ粦瀹氬埌 LLM 鍜?LangGraph Agent")
    print("  5. 宸ュ叿瀹炵幇涓?Agent 浠ｇ爜瀹屽叏瑙ｈ€?)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

