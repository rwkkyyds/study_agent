"""
Demo2: 鐢?LangGraph 鎵嬪姩鏋勫缓 ReAct Agent锛堢櫧鐩掔増锛? 
ReAct Agent 鏄竴绉嶇粡鍏哥殑 Agent 鏋舵瀯锛?鏍稿績鎬濇兂鏄 Agent 鍦ㄦ帹鐞嗚繃绋嬩腑涓嶆柇寰幆锛氭€濊€冿紙Reasoning锛夆啋 琛屽姩锛圓cting锛夆啋 瑙傚療锛圤bservation锛夛紝
鐩村埌瀹屾垚浠诲姟銆傛瘡涓€姝ワ紝Agent 閮藉彲浠ラ€夋嫨鐩存帴鍥炵瓟鐢ㄦ埛闂锛屾垨鑰呰皟鐢ㄥ伐鍏疯幏鍙栨洿澶氫俊鎭紝鍐嶇户缁帹鐞嗐€?鍔熻兘锛氱敤 StateGraph 鏄惧紡瀹氫箟 Agent 鐨勬帹鐞嗗惊鐜紝鑰岄潪 create_agent 榛戠洅
鏍稿績锛欰gent Node 鈫?Conditional Edge 鈫?Tool Node 鈫?寰幆
渚濊禆锛歭angchain-openai, langgraph, langchain-core锛堝凡鏈夛級
鍓嶇疆锛氬厛杩愯 demo1_langgraph_basics.py 鐞嗚В StateGraph 鍩虹
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import math
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage 
# ToolMessage 鏄伐鍏疯皟鐢ㄧ殑娑堟伅绫诲瀷锛屽寘鍚?tool_calls 瀛楁锛孡LM 璋冪敤宸ュ叿鏃惰繑鍥?ToolMessage锛岄噷闈㈡湁 tool_calls 鍒楄〃锛岃褰曚簡瑕佽皟鐢ㄥ摢浜涘伐鍏峰拰鍙傛暟銆?# BaseMessage 鏄墍鏈夋秷鎭被鍨嬬殑鍩虹被锛孉gentState 涓殑 messages 鏄?BaseMessage 鍒楄〃锛屽彲浠ュ寘鍚?HumanMessage銆丄IMessage銆乀oolMessage 绛変笉鍚岀被鍨嬬殑娑堟伅銆?from langgraph.graph import StateGraph, START, END 
# START 鍜?END 鏄?StateGraph 涓殑鐗规畩鑺傜偣锛屽垎鍒〃绀哄浘鐨勫紑濮嬪拰缁撴潫銆?# START 鏄?Agent 鎺ㄧ悊鐨勫叆鍙ｏ紝END 鏄帹鐞嗗畬鎴愮殑鍑哄彛銆?# 鍦ㄦ瀯寤?StateGraph 鏃讹紝鎴戜滑浼氫粠 START 鑺傜偣鍑哄彂锛屽畾涔?Agent Node銆丆onditional Edge銆乀ool Node 绛夎妭鐐瑰拰杈癸紝鏈€缁堝彲鑳戒細鏈変竴浜涜矾寰勯€氬悜 END 鑺傜偣锛岃〃绀烘帹鐞嗙粨鏉熴€?from langgraph.prebuilt import ToolNode 
# ToolNode 鏄?LangGraph 鎻愪緵鐨勯鏋勫缓鑺傜偣绫诲瀷锛岀敤浜庢墽琛屽伐鍏疯皟鐢ㄣ€?# 鎴戜滑鍦?StateGraph 涓坊鍔犱竴涓?ToolNode锛屼紶鍏ュ彲鐢ㄥ伐鍏峰垪琛紝ToolNode 浼氭牴鎹?LLM 鐨?tool_calls 鑷姩鎵ц鐩稿簲宸ュ叿锛屽苟灏嗙粨鏋滆拷鍔犲埌 State.messages 涓€?import operator


# ========== 閰嶇疆 ==========
ZHIPU_API_KEY = __import__("os").environ.get("ZHIPU_API_KEY")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 1. 瀹氫箟宸ュ叿 ==========
@tool
def calculator(expression: str) -> str:
    """璁＄畻鏁板琛ㄨ揪寮忋€傛敮鎸佸姞鍑忎箻闄ゃ€佸箓杩愮畻銆佸紑鏂圭瓑銆?    杈撳叆绀轰緥: '2 + 3 * 4', 'sqrt(16)', '2 ** 10'
    """
    try:
        allowed = {k: v for k, v in math.__dict__.items() if not k.startswith("_")} # 鍏佽 math 妯″潡涓殑鍑芥暟锛堝 sqrt銆乸ow 绛夛級
        result = eval(expression, {"__builtins__": {}}, allowed) # 绂佹璁块棶鍐呯疆鍑芥暟锛岄槻姝㈠畨鍏ㄩ闄?        return str(result)
    except Exception as e:
        return f"璁＄畻閿欒: {e}"


@tool
def knowledge_base(query: str) -> str:
    """鏌ヨ鍐呴儴鐭ヨ瘑搴擄紝鑾峰彇鎶€鏈枃妗ｃ€佷骇鍝佷俊鎭瓑銆?    褰撶敤鎴烽棶鍒版妧鏈蹇碉紙濡?RAG銆丄gent銆丷eAct銆丮ilvus銆丩angGraph锛夋椂浣跨敤姝ゅ伐鍏枫€?    """
    kb = {
        "rag": "RAG锛堟绱㈠寮虹敓鎴愶級= 妫€绱㈠閮ㄧ煡璇?+ LLM 鐢熸垚鍥炵瓟銆傛牳蹇冪粍浠讹細鏂囨。瑙ｆ瀽銆佸悜閲忓寲銆佸悜閲忓簱銆佹绱€侀噸鎺掋€佺敓鎴愩€?,
        "agent": "Agent = LLM锛堝ぇ鑴戯級+ Tools锛堟墜鑴氾級+ 鎺ㄧ悊寰幆銆傛牳蹇冭兘鍔涳細鑷富鍐崇瓥璋冪敤鍝釜宸ュ叿銆佹寜浠€涔堥『搴忚皟鐢ㄣ€?,
        "react": "ReAct = Reasoning + Acting銆傛瘡涓€姝ワ細Thought锛堟€濊€冿級鈫?Action锛堣鍔級鈫?Observation锛堣瀵燂級锛屽惊鐜洿鍒板畬鎴愪换鍔°€?,
        "langgraph": "LangGraph 鏄?LangChain 鍥㈤槦鐨?Agent 妗嗘灦锛岀敤 StateGraph 鏄惧紡瀹氫箟宸ヤ綔娴侊紝姣?create_agent 鏇寸伒娲诲彲鎺с€?,
        "milvus": "Milvus 鏄敓浜х骇鍚戦噺鏁版嵁搴擄紝鏀寔鍗佷嚎绾у悜閲忔绱紝Docker 閮ㄧ讲锛孒NSW 绱㈠紩銆?,
    }
    query_lower = query.lower()
    results = []
    for key, value in kb.items():
        if key in query_lower:
            results.append(value)
    return "\n".join(results) if results else f"鐭ヨ瘑搴撲腑鏈壘鍒颁笌 '{query}' 鐩稿叧鐨勪俊鎭€?


@tool
def get_current_time() -> str:
    """鑾峰彇褰撳墠鏃ユ湡鍜屾椂闂淬€傚綋鐢ㄦ埛闂?鐜板湪鍑犵偣'銆?浠婂ぉ鍑犲彿'鏃朵娇鐢ㄣ€?""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


TOOLS = [calculator, knowledge_base, get_current_time]


# ========== 2. 瀹氫箟 Agent State ==========
# State 鏄浘涓祦鍔ㄧ殑鏁版嵁
# messages 鐢?Annotated[list, operator.add] 琛ㄧず"杩藉姞"鑰岄潪"瑕嗙洊"
# 杩欐牱姣忎釜 Node 鐨勮繑鍥炲€间細杩藉姞鍒版秷鎭垪琛紝鑰屼笉鏄浛鎹?class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add] 
    #operators.add 琛ㄧず鍦?StateGraph 涓繖涓瓧娈电殑鏇存柊鏂瑰紡鏄拷鍔狅紙鑰岄潪瑕嗙洊锛夈€傛瘡娆?Agent Node 鎴?Tool Node 杩斿洖鏂扮殑娑堟伅鏃讹紝閮戒細杩藉姞鍒?messages 鍒楄〃涓紝淇濈暀瀹屾暣鐨勬秷鎭巻鍙层€?    #Annotated 鏄?Python 3.9+ 鐨勭被鍨嬫敞瑙ｅ伐鍏凤紝杩欓噷鐢ㄦ潵鏍囪 messages 鏄竴涓垪琛?

# ========== 3. 瀹氫箟 Agent Node ==========
# Agent Node 鐨勮亴璐ｏ細璋冪敤 LLM锛岃 LLM 鍐冲畾鏄洖绛旇繕鏄皟鐢ㄥ伐鍏?def agent_node(state: AgentState) -> dict:
    """
    Agent 鑺傜偣锛氳皟鐢?LLM 鍐崇瓥
    - 濡傛灉 LLM 鍐冲畾璋冪敤宸ュ叿 鈫?杩斿洖 tool_calls锛圓IMessage 甯?tool_calls锛?    - 濡傛灉 LLM 鍐冲畾鐩存帴鍥炵瓟 鈫?杩斿洖鏅€?AIMessage锛堟棤 tool_calls锛?    """
    print("  [Agent Node] 璋冪敤 LLM 鍐崇瓥...")

    llm = ChatOpenAI(
        api_key=ZHIPU_API_KEY,
        base_url=ZHIPU_BASE_URL,
        model="glm-4-flash",
        temperature=0,
    )

    # 缁戝畾宸ュ叿锛岃 LLM 鐭ラ亾鏈夊摢浜涘伐鍏峰彲鐢?    llm_with_tools = llm.bind_tools(TOOLS)

    # 璋冪敤 LLM锛堜紶鍏ュ畬鏁存秷鎭巻鍙诧級
    response = llm_with_tools.invoke(state["messages"])

    # 鎵撳嵃 LLM 鐨勫喅绛?    if response.tool_calls:
        for tc in response.tool_calls:
            print(f"    鈫?LLM 鍐冲畾璋冪敤宸ュ叿: {tc['name']}({tc['args']})")
    else:
        print(f"    鈫?LLM 鍐冲畾鐩存帴鍥炵瓟")

    # 杩斿洖杩藉姞鍒?messages 鐨勬柊娑堟伅
    return {"messages": [response]}
 #eg: {"messages": [AIMessage(content="鍥炵瓟鍐呭",  tool_calls=[{"name": "calculator", "args": {"expression": "2 + 2"}}])]} 
 # 鎴?{"messages": [AIMessage(content="鐩存帴鍥炵瓟鍐呭")]}锛? # StateGraph 浼氭牴鎹?tool_calls 鏄惁瀛樺湪鏉ュ垽鏂笅涓€姝ヨ蛋鍝釜鍒嗘敮銆?

# ========== 4. 瀹氫箟 Conditional Edge ==========
# 鍒ゆ柇鏄惁闇€瑕佺户缁皟鐢ㄥ伐鍏?def should_continue(state: AgentState) -> str:
    """
    鏉′欢璺敱锛?    - 鏈€鍚庝竴鏉℃秷鎭湁 tool_calls 鈫?鍘?"tools" 鑺傜偣鎵ц宸ュ叿
    - 鏈€鍚庝竴鏉℃秷鎭病鏈?tool_calls 鈫?缁撴潫
    """
    last_message = state["messages"][-1]
    #eg: 鏈€鍚庝竴鏉℃秷鎭槸 
    # AIMessage(content="鍥炵瓟鍐呭",  tool_calls=[{"name": "calculator", "args": {"expression": "2 + 2"}}])锛?    # 鍒欐湁宸ュ叿璋冪敤锛涘鏋滄槸 AIMessage(content="鐩存帴鍥炵瓟鍐呭") 鍒欐棤宸ュ叿璋冪敤銆?
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        print("  [Conditional Edge] 鏈夊伐鍏疯皟鐢?鈫?鍘绘墽琛屽伐鍏?)
        return "tools"
    else:
        print("  [Conditional Edge] 鏃犲伐鍏疯皟鐢?鈫?缁撴潫")
        return "end"


# ========== 5. 鏋勫缓 LangGraph Agent ==========
def build_langgraph_agent() -> StateGraph:  
    #StateGraph閫氫織鏄撴噦鐨勮灏辨槸涓€涓湁鍚戝浘锛岃妭鐐逛唬琛?Agent 鐨勪笉鍚岀姸鎬侊紙濡傛€濊€冦€佽鍔ㄣ€佽瀵燂級锛?    # 杈逛唬琛ㄧ姸鎬佷箣闂寸殑杞Щ锛堝鏉′欢鍒ゆ柇銆佸伐鍏疯皟鐢級銆傞€氳繃瀹氫箟 StateGraph锛屾垜浠彲浠ユ竻鏅板湴鎻忚堪 Agent 鐨勬帹鐞嗘祦绋嬪拰寰幆閫昏緫銆?    """
    鐢?StateGraph 鎵嬪姩鏋勫缓 ReAct Agent锛?
    鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?    鈹? START   鈹?    鈹斺攢鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹?         鈹?    鈹屸攢鈹€鈹€鈹€鈻尖攢鈹€鈹€鈹€鈹€鈹?    鈹? agent   鈹?鈫?璋冪敤 LLM 鍐崇瓥
    鈹斺攢鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹?         鈹?    鈹屸攢鈹€鈹€鈹€鈻尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?    鈹?should_continue鈹?鈫?鏉′欢鍒ゆ柇
    鈹斺攢鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹?       鈹?        鈹?    "tools"    "end"
       鈹?        鈹?    鈹屸攢鈹€鈻尖攢鈹€鈹€鈹?    鈹?    鈹?tools 鈹?    鈹? 鈫?鎵ц宸ュ叿锛岀粨鏋滆拷鍔犲埌 messages
    鈹斺攢鈹€鈹攢鈹€鈹€鈹?    鈹?       鈹?        鈹?       鈹斺攢鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹?            鈹?       鍥炲埌 agent锛堝惊鐜級
    """
    graph = StateGraph(AgentState) # 瀹氫箟 StateGraph锛孲tate 绫诲瀷涓?AgentState

    # 娣诲姞鑺傜偣
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))

    # 娣诲姞杈?    graph.add_edge(START, "agent")                    # START 鈫?agent

    # 鏉′欢杈癸細agent 鈫?should_continue 鈫?tools 鎴?end
    graph.add_conditional_edges(
        "agent",                                       # 浠?agent 鍑哄彂
        should_continue,                               # 璺敱鍑芥暟
        {
            "tools": "tools",                          # 鏈夊伐鍏疯皟鐢?鈫?鍘?tools
            "end": END                                 # 鏃犲伐鍏疯皟鐢?鈫?缁撴潫
        }
    )

    # tools 鎵ц瀹屽悗锛屽洖鍒?agent 缁х画鎺ㄧ悊
    graph.add_edge("tools", "agent")

    return graph.compile()


# ========== 6. 杩愯娴嬭瘯 ==========
def run_demo():
    """杩愯 LangGraph Agent Demo"""
    agent = build_langgraph_agent()

    questions = [
        "璁＄畻涓€涓?(15 * 8 + 120) / 4 绛変簬澶氬皯锛?,
        "浠€涔堟槸 LangGraph锛熷畠鍜屼紶缁?Agent 鏈変粈涔堝尯鍒紵",
        "鐜板湪鍑犵偣浜嗭紵鍙﹀甯垜绠椾竴涓?2 鐨?20 娆℃柟鏄灏戯紵",
    ]

    for i, q in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"闂 {i+1}: {q}")
        print("=" * 60)

        try:
            # invoke 浼犲叆鍒濆娑堟伅
            result = agent.invoke({"messages": [HumanMessage(content=q)]})

            # 鏈€鍚庝竴鏉℃秷鎭槸鏈€缁堝洖绛?            final_message = result["messages"][-1]
            print(f"\n[鏈€缁堝洖绛擼 {final_message.content}")
            

            # 鎵撳嵃瀹屾暣娑堟伅閾撅紙璋冭瘯鐢級
            print(f"\n--- 娑堟伅閾?({len(result['messages'])} 鏉? ---")
            for j, msg in enumerate(result["messages"]):
                msg_type = type(msg).__name__
                content_preview = msg.content[:80] if msg.content else "(鏃犲唴瀹?"
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"  [{j}] {msg_type}: tool_call 鈫?{tc['name']}")
                else:
                    print(f"  [{j}] {msg_type}: {content_preview}")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()


# ========== 涓诲嚱鏁?==========
if __name__ == "__main__":
    try:
        print("=" * 60)
        print("LangGraph ReAct Agent锛堢櫧鐩掔増锛?)
        print("=" * 60)
        print("""
    涓?Section 1 鐨?create_agent 瀵规瘮锛?
    create_agent锛堥粦鐩掞級:          LangGraph锛堢櫧鐩掞級:
      涓€琛屼唬鐮佸垱寤?                   鎵嬪姩瀹氫箟姣忎釜鑺傜偣
      鍐呴儴鑷姩澶勭悊寰幆                浣犳帶鍒跺惊鐜€昏緫
      闅句互鑷畾涔?                     瀹屽叏鍙畾鍒?
    鏈?Demo 灞曠ず LangGraph 鐨勬墜鍔ㄦ瀯寤鸿繃绋嬶細
      1. Agent Node锛氳皟鐢?LLM 鍐崇瓥
      2. Conditional Edge锛氬垽鏂槸鍚﹁皟鐢ㄥ伐鍏?      3. Tool Node锛氭墽琛屽伐鍏?      4. 寰幆锛歵ools 鈫?agent 鈫?鍒ゆ柇 鈫?...
        """)

        run_demo()

        print(f"\n{'=' * 60}")
        print("[OK] LangGraph Agent Demo 瀹屾垚锛?)
        print("鏍稿績鏀惰幏锛?)
        print("  1. LangGraph 鐢?StateGraph 鏄惧紡瀹氫箟 Agent 鎺ㄧ悊寰幆")
        print("  2. Agent Node 璋冪敤 LLM 鍐崇瓥锛堝洖绛?or 璋冪敤宸ュ叿锛?)
        print("  3. Conditional Edge 鎺у埗寰幆锛堢户缁皟鐢ㄥ伐鍏?or 缁撴潫锛?)
        print("  4. Tool Node 鎵ц宸ュ叿锛岀粨鏋滆拷鍔犲埌 State.messages")
        print("  5. 姣?create_agent 鏇寸伒娲伙紝鍙嚜瀹氫箟姣忎釜鐜妭")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

