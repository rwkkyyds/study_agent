"""
demo3_research_assistant.py - 瀹屾暣鐮旂┒鍔╂墜锛圵eek3 缁煎悎 Demo锛?
鍏ㄩ儴鐢ㄤ綘瀛﹁繃鐨?LangGraph 缁勪欢锛?- S1: ReAct 鍐崇瓥锛坅gent_node + should_continue 寰幆锛?- S2: StateGraph + 鑺傜偣 + 杈?+ 鏉′欢璺敱
- S3: @tool 瀹氫箟涓変釜宸ュ叿
- S4: SQLite 鏁版嵁搴撴煡璇?- S5: MemorySaver 浼氳瘽璁板繂 + thread_id
- S6: try-except 寮傚父澶勭悊

渚濊禆锛歠aiss-cpu, langchain-openai, langgraph
"""

import sys, io, operator, logging, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import faiss
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ZHIPU_API_KEY = __import__("os").environ.get("ZHIPU_API_KEY")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# ========== S4: SQLite 涓氬姟鏁版嵁搴?==========
db = sqlite3.connect(":memory:", check_same_thread=False)
db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, role TEXT, department TEXT)")
db.executemany("INSERT INTO users VALUES (?,?,?,?)", [
    (1, "寮犱笁", "AI宸ョ▼甯?, "鎶€鏈儴"),
    (2, "鏉庡洓", "浜у搧缁忕悊", "浜у搧閮?),
    (3, "鐜嬩簲", "鏁版嵁鍒嗘瀽甯?, "鏁版嵁閮?),
    (4, "璧靛叚", "AI鏋舵瀯甯?, "鎶€鏈儴"),
    (5, "瀛欎竷", "鍓嶇宸ョ▼甯?, "鎶€鏈儴"),
])

# ========== FAISS 鐭ヨ瘑搴?==========
KNOWLEDGE = [
    {"topic": "RAG", "content": "RAG閫氳繃妫€绱㈠閮ㄧ煡璇嗗簱澧炲己LLM鍥炵瓟銆傛祦绋嬶細鍒嗗潡鈫扙mbedding鈫掑悜閲忓簱鈫掓绱⑩啋Prompt鈫掔敓鎴愩€?},
    {"topic": "Agent", "content": "Agent鏄嚜涓诲喅绛朅I绯荤粺銆俁eAct寰幆(鎬濊€冣啋琛屽姩鈫掕瀵?銆侺angGraph鏋勫缓宸ヤ綔娴併€?},
    {"topic": "LangChain", "content": "LangChain鏄疞LM搴旂敤妗嗘灦銆傜粍浠讹細Prompt/LLM/Parser銆侺CEL绠￠亾绗︾粍鍚堛€?},
    {"topic": "Milvus", "content": "Milvus鏄敓浜х骇鍚戦噺鏁版嵁搴撱€傛敮鎸佸崄浜跨骇鍚戦噺銆丠NSW/IVF绱㈠紩銆佸垎甯冨紡閮ㄧ讲銆?},
    {"topic": "Embedding", "content": "Embedding鎶婃枃鏈浆鍚戦噺銆傛ā鍨嬶細OpenAI text-embedding-3-small銆丅GE绯诲垪銆?},
    {"topic": "瀹归敊", "content": "Agent涓夌骇瀹归敊锛氬紓甯告崟鑾封啋鎸囨暟閫€閬块噸璇?tenacity)鈫扚allback宸ュ叿閾鹃檷绾с€?},
]

def build_faiss_index():
    dim = 128
    index = faiss.IndexFlatIP(dim)
    vectors = []
    for doc in KNOWLEDGE:
        np.random.seed(hash(doc["content"]) % (2**31))
        vec = np.random.randn(dim).astype(np.float32)
        faiss.normalize_L2(vec.reshape(1, -1))
        vectors.append(vec)
    vectors_np = np.array(vectors)
    faiss.normalize_L2(vectors_np)
    index.add(vectors_np)
    return index

faiss_index = build_faiss_index()

# ========== S3: 涓変釜宸ュ叿锛堝甫 S6 寮傚父澶勭悊锛?=========
@tool
def web_search(query: str) -> str:
    """鎼滅储浜掕仈缃戣幏鍙栨渶鏂颁俊鎭€傜敤浜庢煡璇㈠疄鏃舵柊闂汇€佹妧鏈姩鎬併€?""
    logger.info(f"[鎼滅储] {query}")
    try:
        return f"鎼滅储缁撴灉锛氬叧浜?{query}'锛岃棰嗗煙姝ｅ湪蹇€熷彂灞曪紝澶氬浼佷笟宸插姞澶ф姇鍏ャ€?
    except Exception as e:
        return f"[ERROR] 鎼滅储澶辫触: {e}"

@tool
def knowledge_search(query: str) -> str:
    """浠庣煡璇嗗簱妫€绱㈡妧鏈枃妗ｃ€傜敤浜庢煡璇AG銆丄gent銆丩angChain绛夋蹇点€?""
    logger.info(f"[妫€绱 {query}")
    try:
        np.random.seed(hash(query) % (2**31))
        query_vec = np.random.randn(128).astype(np.float32)
        faiss.normalize_L2(query_vec.reshape(1, -1))
        scores, indices = faiss_index.search(query_vec.reshape(1, -1), 2)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(KNOWLEDGE):
                doc = KNOWLEDGE[idx]
                results.append(f"[{doc['topic']}] {doc['content']}")
        return "\n---\n".join(results) if results else "鏈壘鍒扮浉鍏冲唴瀹广€?
    except Exception as e:
        return f"[ERROR] 妫€绱㈠け璐? {e}"

@tool
def sql_query(sql: str) -> str:
    """鎵цSQL鏌ヨ鏁版嵁搴撱€傝〃锛歶sers(id, name, role, department)銆傚彧鍏佽SELECT銆?""
    logger.info(f"[SQL] {sql}")
    try:
        if not sql.strip().upper().startswith("SELECT"):
            return "[ERROR] 鍙厑璁?SELECT 鏌ヨ"
        cursor = db.execute(sql)
        rows = cursor.fetchall()
        return f"鏌ヨ缁撴灉 ({len(rows)} 鏉?: {rows}"
    except Exception as e:
        return f"[ERROR] SQL鎵ц澶辫触: {e}"

TOOLS = [web_search, knowledge_search, sql_query]

# ========== S2: State + Agent Node + Conditional Edge ==========
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

def agent_node(state: AgentState) -> dict:
    """Agent 鑺傜偣锛氳皟鐢?LLM 鍐崇瓥"""
    llm = ChatOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL, model="glm-4-flash", temperature=0)
    response = llm.bind_tools(TOOLS).invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    """鏉′欢璺敱锛氭湁 tool_calls 鈫?tools锛涘惁鍒?鈫?end"""
    last = state["messages"][-1]
    return "tools" if isinstance(last, AIMessage) and last.tool_calls else "end"

# ========== S2+S5: 鏋勫缓鍥撅紙鍚?MemorySaver锛?=========
def build_research_assistant():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")

    # S5: MemorySaver 浼氳瘽璁板繂
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

# ========== 婕旂ず ==========
if __name__ == "__main__":
    print("=" * 60)
    print("Week3 缁煎悎 Demo: 鐮旂┒鍔╂墜 Agent")
    print("S1:ReAct鍐崇瓥 S2:LangGraph S3:宸ュ叿 S4:DB S5:璁板繂 S6:瀹归敊")
    print("=" * 60)

    agent = build_research_assistant()
    # S5: thread_id 闅旂浼氳瘽
    config = {"configurable": {"thread_id": "research_session_001"}}

    tests = [
        ("鎼滅储", "AI Agent 鏈€鏂拌繘灞?),
        ("妫€绱?, "浠€涔堟槸RAG"),
        ("SQL", "鏌ヨ鎶€鏈儴鏈夊灏戜汉"),
        ("闂茶亰", "浣犲ソ"),
    ]

    for label, query in tests:
        print(f"\n--- [{label}] {query} ---")
        try:
            result = agent.invoke({"messages": [HumanMessage(content=query)]}, config=config)
            print(f"[鏈€缁堝洖绛擼 {result['messages'][-1].content}")
        except Exception as e:
            logger.error(f"鎵ц澶辫触: {e}")
            print(f"[ERROR] {e}")

    print("\n" + "=" * 60)
    print("Week3 鐭ヨ瘑鐐瑰叏閮ㄤ覆鑱旓細")
    print("  S1: Agent 鑷富鍐崇瓥璋冪敤鍝釜宸ュ叿锛圧eAct锛?)
    print("  S2: StateGraph + agent_node + should_continue + ToolNode")
    print("  S3: @tool 瀹氫箟鎼滅储/妫€绱?SQL涓変釜宸ュ叿")
    print("  S4: SQLite 鏁版嵁搴?+ FAISS 鍚戦噺搴?)
    print("  S5: MemorySaver 浼氳瘽璁板繂 + thread_id 闅旂")
    print("  S6: try-except 寮傚父澶勭悊")
    print("=" * 60)

