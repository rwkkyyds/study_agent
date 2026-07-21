"""
demo2_rag_agent.py - 鐭ヨ瘑搴撴绱?Agent锛圠angGraph StateGraph + FAISS锛?
鐢ㄤ綘瀛﹁繃鐨勭粍浠讹細
- StateGraph + agent_node + should_continue + ToolNode
- FAISS 鍚戦噺妫€绱紙Section 4 鐭ヨ瘑锛?- @tool 瀹氫箟妫€绱㈠伐鍏?
渚濊禆锛歠aiss-cpu, langchain-openai, langgraph
"""

import sys, io, operator, logging
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import faiss
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ZHIPU_API_KEY = __import__("os").environ.get("ZHIPU_API_KEY")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# ========== 1. 鐭ヨ瘑搴?+ FAISS 绱㈠紩 ==========
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

# ========== 2. 妫€绱㈠伐鍏?==========
@tool
def knowledge_search(query: str) -> str:
    """浠庣煡璇嗗簱妫€绱㈡妧鏈枃妗ｃ€傝緭鍏ラ棶棰樺叧閿瘝锛岃繑鍥炴渶鐩稿叧鏂囨。銆?""
    logger.info(f"[妫€绱 {query}")
    np.random.seed(hash(query) % (2**31))
    query_vec = np.random.randn(128).astype(np.float32)
    faiss.normalize_L2(query_vec.reshape(1, -1))
    scores, indices = faiss_index.search(query_vec.reshape(1, -1), 2)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(KNOWLEDGE):
            doc = KNOWLEDGE[idx]
            results.append(f"[{doc['topic']}] {doc['content']} (鐩镐技搴?{score:.3f})")
    return "\n---\n".join(results) if results else "鏈壘鍒扮浉鍏冲唴瀹广€?

TOOLS = [knowledge_search]

# ========== 3. State + Agent Node + Conditional Edge ==========
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

def agent_node(state: AgentState) -> dict:
    llm = ChatOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL, model="glm-4-flash", temperature=0)
    response = llm.bind_tools(TOOLS).invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    return "tools" if isinstance(last, AIMessage) and last.tool_calls else "end"

# ========== 4. 鏋勫缓鍥?==========
def build_rag_agent():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")
    return graph.compile()

# ========== 5. 婕旂ず ==========
if __name__ == "__main__":
    print("=" * 60)
    print("demo2: 鐭ヨ瘑搴撴绱?Agent锛圠angGraph + FAISS锛?)
    print("=" * 60)

    agent = build_rag_agent()

    for q in ["浠€涔堟槸RAG锛屽師鐞嗘槸浠€涔?, "鍚戦噺鏁版嵁搴撴湁鍝簺閫夋嫨"]:
        print(f"\n--- 闂: {q} ---")
        result = agent.invoke({"messages": [HumanMessage(content=q)]})
        print(f"[鏈€缁堝洖绛擼 {result['messages'][-1].content}")

