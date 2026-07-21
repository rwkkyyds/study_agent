"""
Demo2: ReAct Agent 瀹屾暣鎺ㄧ悊寰幆
鍔熻兘锛氬畾涔夊伐鍏?鈫?鍒涘缓 ReAct Agent 鈫?杩愯鎺ㄧ悊寰幆
鏍稿績锛氱悊瑙?Thought 鈫?Action 鈫?Observation 鐨勫惊鐜帹鐞嗚繃绋?渚濊禆锛歭angchain-openai, langchain锛堝凡鏈夛級
娉ㄦ剰锛歭angchain 1.3.x 浣跨敤 create_agent 鏂?API锛堝熀浜?langgraph锛?鍓嶇疆锛氬厛杩愯 demo1_tool_basics.py 鐞嗚В宸ュ叿瀹氫箟
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import math
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent


# ========== 閰嶇疆 ==========
ZHIPU_API_KEY = __import__("os").environ.get("ZHIPU_API_KEY")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 1. 瀹氫箟宸ュ叿 ==========
# @tool 瑁呴グ鍣ㄥ皢鏅€氬嚱鏁拌浆涓?Agent 鍙皟鐢ㄧ殑宸ュ叿
# docstring 闈炲父閲嶈锛欰gent 鏍规嵁瀹冩潵鍐冲畾浣曟椂璋冪敤杩欎釜宸ュ叿

@tool
def calculator(expression: str) -> str:
    """璁＄畻鏁板琛ㄨ揪寮忋€傛敮鎸佸姞鍑忎箻闄ゃ€佸箓杩愮畻銆佸紑鏂圭瓑銆?    杈撳叆绀轰緥: "2 + 3 * 4", "sqrt(16)", "2 ** 10"
    """
    try:
        # 瀹夊叏鐨勬暟瀛︽眰鍊硷細鍙厑璁?math 妯″潡涓殑鍑芥暟
        allowed = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        result = eval(expression, {"__builtins__": {}}, allowed)
        return str(result)
    except Exception as e:
        return f"璁＄畻閿欒: {e}"


@tool
def knowledge_base(query: str) -> str:
    """鏌ヨ鍐呴儴鐭ヨ瘑搴擄紝鑾峰彇鎶€鏈枃妗ｃ€佷骇鍝佷俊鎭瓑銆?    褰撶敤鎴烽棶鍒版妧鏈蹇碉紙濡?RAG銆丄gent銆丷eAct銆丮ilvus锛夋椂浣跨敤姝ゅ伐鍏枫€?    """
    # 妯℃嫙鐭ヨ瘑搴擄紙鐢熶骇鐜涓鎺?RAG 鎴栨暟鎹簱锛?    kb = {
        "rag": "RAG锛堟绱㈠寮虹敓鎴愶級= 妫€绱㈠閮ㄧ煡璇?+ LLM 鐢熸垚鍥炵瓟銆傛牳蹇冪粍浠讹細鏂囨。瑙ｆ瀽銆佸悜閲忓寲銆佸悜閲忓簱銆佹绱€侀噸鎺掋€佺敓鎴愩€?,
        "agent": "Agent = LLM锛堝ぇ鑴戯級+ Tools锛堟墜鑴氾級+ 鎺ㄧ悊寰幆銆傛牳蹇冭兘鍔涳細鑷富鍐崇瓥璋冪敤鍝釜宸ュ叿銆佹寜浠€涔堥『搴忚皟鐢ㄣ€?,
        "react": "ReAct = Reasoning + Acting銆傛瘡涓€姝ワ細Thought锛堟€濊€冿級鈫?Action锛堣鍔級鈫?Observation锛堣瀵燂級锛屽惊鐜洿鍒板畬鎴愪换鍔°€?,
        "milvus": "Milvus 鏄敓浜х骇鍚戦噺鏁版嵁搴擄紝鏀寔鍗佷嚎绾у悜閲忔绱紝Docker 閮ㄧ讲锛孒NSW 绱㈠紩銆?,
        "langchain": "LangChain 鏄?LLM 搴旂敤寮€鍙戞鏋讹紝鏍稿績缁勪欢锛歅rompt Template銆丱utput Parser銆丩CEL 閾捐矾銆丄gent銆乀ools銆?,
    }
    query_lower = query.lower()
    results = []
    for key, value in kb.items():
        if key in query_lower:
            results.append(value)
    if results:
        return "\n".join(results)
    return f"鐭ヨ瘑搴撲腑鏈壘鍒颁笌 '{query}' 鐩稿叧鐨勪俊鎭€?


@tool
def get_current_time() -> str:
    """鑾峰彇褰撳墠鏃ユ湡鍜屾椂闂淬€傚綋鐢ㄦ埛闂?鐜板湪鍑犵偣'銆?浠婂ぉ鍑犲彿'鏃朵娇鐢ㄣ€?""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ========== 2. 鍒涘缓 Agent ==========
def create_react_agent_demo():
    """
    鍒涘缓 ReAct Agent锛坙angchain 1.3.x 鏂?API锛夛細
    - model锛歀LM锛堝ぇ鑴戯級
    - tools锛氬伐鍏峰垪琛紙鎵嬭剼锛?    - system_prompt锛氳涓烘寚瀵?
    鍐呴儴鑷姩澶勭悊锛?    - ReAct 鎺ㄧ悊寰幆锛圱hought 鈫?Action 鈫?Observation锛?    - 宸ュ叿璋冪敤瑙ｆ瀽
    - 寰幆缁堟鏉′欢锛圓gent 鍐冲畾涓嶅啀璋冪敤宸ュ叿鏃跺仠姝級
    """
    # LLM锛堝ぇ鑴戯級
    llm = ChatOpenAI(
        api_key=ZHIPU_API_KEY,
        base_url=ZHIPU_BASE_URL,
        model="glm-4-flash",
        temperature=0,
    )

    # 宸ュ叿鍒楄〃锛堟墜鑴氾級
    tools = [calculator, knowledge_base, get_current_time]

    # System Prompt锛氭寚瀵?Agent 鐨勮涓烘ā寮?    system_prompt = (
        "浣犳槸涓€涓櫤鑳藉姪鎵嬶紝鍙互浣跨敤宸ュ叿鏉ュ洖绛旈棶棰樸€俓n"
        "鍙敤宸ュ叿锛氳绠楀櫒(calculator)銆佺煡璇嗗簱鏌ヨ(knowledge_base)銆佹椂闂存煡璇?get_current_time)\n\n"
        "璇锋寜浠ヤ笅姝ラ鎬濊€冿細\n"
        "1. 鍒嗘瀽鐢ㄦ埛闂锛屽垽鏂槸鍚﹂渶瑕佽皟鐢ㄥ伐鍏穃n"
        "2. 濡傛灉闇€瑕侊紝閫夋嫨鍚堥€傜殑宸ュ叿骞惰皟鐢╘n"
        "3. 鏍规嵁宸ュ叿杩斿洖鐨勭粨鏋滐紝缁х画鎬濊€冩垨缁欏嚭鏈€缁堝洖绛擻n"
        "4. 涓嶈缂栭€犱俊鎭紝璇ョ敤宸ュ叿鏃跺繀椤荤敤宸ュ叿"
    )

    # create_agent锛氫竴琛屼唬鐮佸垱寤哄畬鏁寸殑 ReAct Agent
    # 杩斿洖鐨勬槸 CompiledStateGraph锛屽彲鐩存帴 invoke
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    return agent


# ========== 3. 杩愯娴嬭瘯 ==========
def run_demo():
    """杩愯 Agent Demo锛屽睍绀?ReAct 鎺ㄧ悊杩囩▼"""
    agent = create_react_agent_demo()

    questions = [
        # 闇€瑕佽皟鐢ㄥ伐鍏风殑闂
        "璁＄畻涓€涓?(15 * 8 + 120) / 4 绛変簬澶氬皯锛?,
        # 闇€瑕佹煡璇㈢煡璇嗗簱鐨勯棶棰?        "浠€涔堟槸 RAG锛熷畠鍜?Agent 鏈変粈涔堝尯鍒紵",
        # 闇€瑕佺粍鍚堝涓伐鍏风殑闂
        "鐜板湪鍑犵偣浜嗭紵鍙﹀甯垜绠椾竴涓?2 鐨?20 娆℃柟鏄灏戯紵",
    ]

    for i, q in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"闂 {i+1}: {q}")
        print(f"{'=' * 60}")

        try:
            # invoke 浼犲叆娑堟伅鍒楄〃锛孉gent 鑷姩鎵ц鎺ㄧ悊寰幆
            result = agent.invoke({"messages": [("human", q)]})
            # 鏈€鍚庝竴鏉℃秷鎭槸 Agent 鐨勬渶缁堝洖绛?            final_message = result["messages"][-1]
            print(f"\n[鏈€缁堝洖绛擼 {final_message.content}")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print("[OK] Agent Demo 瀹屾垚锛?)
    print("鏍稿績鏀惰幏锛?)
    print("  1. Agent = LLM + Tools + 鎺ㄧ悊寰幆")
    print("  2. ReAct锛歍hought 鈫?Action 鈫?Observation 寰幆")
    print("  3. @tool 瑁呴グ鍣ㄥ畾涔夊伐鍏凤紝docstring 鏄?Agent 鍐崇瓥渚濇嵁")
    print("  4. create_agent 涓€琛屼唬鐮佸垱寤哄畬鏁?Agent")


# ========== 涓诲嚱鏁?==========
if __name__ == "__main__":
    try:
        run_demo()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback # 鎵撳嵃瀹屾暣閿欒鍫嗘爤锛屾柟渚胯皟璇?        traceback.print_exc()

