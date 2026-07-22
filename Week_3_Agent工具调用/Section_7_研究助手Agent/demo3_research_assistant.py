"""
demo3_research_assistant.py - 完整研究助手（Week3 综合 Demo）

全部用你学过的 LangGraph 组件：
- S1: ReAct 决策（agent_node + should_continue 循环）
- S2: StateGraph + 节点 + 边 + 条件路由
- S3: @tool 定义三个工具
- S4: SQLite 数据库查询
- S5: MemorySaver 会话记忆 + thread_id
- S6: try-except 异常处理

依赖：faiss-cpu, langchain-openai, langgraph
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

ZHIPU_API_KEY = "70041ddde9824461bfb02fac3f469fc3.pDZCoxOgkovIx1vT"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# ========== S4: SQLite 业务数据库 ==========
db = sqlite3.connect(":memory:", check_same_thread=False)
db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, role TEXT, department TEXT)")
db.executemany("INSERT INTO users VALUES (?,?,?,?)", [
    (1, "张三", "AI工程师", "技术部"),
    (2, "李四", "产品经理", "产品部"),
    (3, "王五", "数据分析师", "数据部"),
    (4, "赵六", "AI架构师", "技术部"),
    (5, "孙七", "前端工程师", "技术部"),
])

# ========== FAISS 知识库 ==========
KNOWLEDGE = [
    {"topic": "RAG", "content": "RAG通过检索外部知识库增强LLM回答。流程：分块→Embedding→向量库→检索→Prompt→生成。"},
    {"topic": "Agent", "content": "Agent是自主决策AI系统。ReAct循环(思考→行动→观察)。LangGraph构建工作流。"},
    {"topic": "LangChain", "content": "LangChain是LLM应用框架。组件：Prompt/LLM/Parser。LCEL管道符组合。"},
    {"topic": "Milvus", "content": "Milvus是生产级向量数据库。支持十亿级向量、HNSW/IVF索引、分布式部署。"},
    {"topic": "Embedding", "content": "Embedding把文本转向量。模型：OpenAI text-embedding-3-small、BGE系列。"},
    {"topic": "容错", "content": "Agent三级容错：异常捕获→指数退避重试(tenacity)→Fallback工具链降级。"},
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

# ========== S3: 三个工具（带 S6 异常处理）==========
@tool
def web_search(query: str) -> str:
    """搜索互联网获取最新信息。用于查询实时新闻、技术动态。"""
    logger.info(f"[搜索] {query}")
    try:
        return f"搜索结果：关于'{query}'，该领域正在快速发展，多家企业已加大投入。"
    except Exception as e:
        return f"[ERROR] 搜索失败: {e}"

@tool
def knowledge_search(query: str) -> str:
    """从知识库检索技术文档。用于查询RAG、Agent、LangChain等概念。"""
    logger.info(f"[检索] {query}")
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
        return "\n---\n".join(results) if results else "未找到相关内容。"
    except Exception as e:
        return f"[ERROR] 检索失败: {e}"

@tool
def sql_query(sql: str) -> str:
    """执行SQL查询数据库。表：users(id, name, role, department)。只允许SELECT。"""
    logger.info(f"[SQL] {sql}")
    try:
        if not sql.strip().upper().startswith("SELECT"):
            return "[ERROR] 只允许 SELECT 查询"
        cursor = db.execute(sql)
        rows = cursor.fetchall()
        return f"查询结果 ({len(rows)} 条): {rows}"
    except Exception as e:
        return f"[ERROR] SQL执行失败: {e}"

TOOLS = [web_search, knowledge_search, sql_query]

# ========== S2: State + Agent Node + Conditional Edge ==========
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

def agent_node(state: AgentState) -> dict:
    """Agent 节点：调用 LLM 决策"""
    llm = ChatOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL, model="glm-4-flash", temperature=0)
    response = llm.bind_tools(TOOLS).invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    """条件路由：有 tool_calls → tools；否则 → end"""
    last = state["messages"][-1]
    return "tools" if isinstance(last, AIMessage) and last.tool_calls else "end"

# ========== S2+S5: 构建图（含 MemorySaver）==========
def build_research_assistant():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")

    # S5: MemorySaver 会话记忆
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

# ========== 演示 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("Week3 综合 Demo: 研究助手 Agent")
    print("S1:ReAct决策 S2:LangGraph S3:工具 S4:DB S5:记忆 S6:容错")
    print("=" * 60)

    agent = build_research_assistant()
    # S5: thread_id 隔离会话
    config = {"configurable": {"thread_id": "research_session_001"}}

    tests = [
        ("搜索", "AI Agent 最新进展"),
        ("检索", "什么是RAG"),
        ("SQL", "查询技术部有多少人"),
        ("闲聊", "你好"),
    ]

    for label, query in tests:
        print(f"\n--- [{label}] {query} ---")
        try:
            result = agent.invoke({"messages": [HumanMessage(content=query)]}, config=config)
            print(f"[最终回答] {result['messages'][-1].content}")
        except Exception as e:
            logger.error(f"执行失败: {e}")
            print(f"[ERROR] {e}")

    print("\n" + "=" * 60)
    print("Week3 知识点全部串联：")
    print("  S1: Agent 自主决策调用哪个工具（ReAct）")
    print("  S2: StateGraph + agent_node + should_continue + ToolNode")
    print("  S3: @tool 定义搜索/检索/SQL三个工具")
    print("  S4: SQLite 数据库 + FAISS 向量库")
    print("  S5: MemorySaver 会话记忆 + thread_id 隔离")
    print("  S6: try-except 异常处理")
    print("=" * 60)
