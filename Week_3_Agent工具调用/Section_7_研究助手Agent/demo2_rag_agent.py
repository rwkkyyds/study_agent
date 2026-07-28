"""
demo2_rag_agent.py - 知识库检索 Agent（LangGraph StateGraph + FAISS）

用你学过的组件：
- StateGraph + agent_node + should_continue + ToolNode
- FAISS 向量检索（Section 4 知识）
- @tool 定义检索工具

依赖：faiss-cpu, langchain-openai, langgraph
"""
import os

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

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# ========== 1. 知识库 + FAISS 索引 ==========
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

# ========== 2. 检索工具 ==========
@tool
def knowledge_search(query: str) -> str:
    """从知识库检索技术文档。输入问题关键词，返回最相关文档。"""
    logger.info(f"[检索] {query}")
    np.random.seed(hash(query) % (2**31))
    query_vec = np.random.randn(128).astype(np.float32)
    faiss.normalize_L2(query_vec.reshape(1, -1))
    scores, indices = faiss_index.search(query_vec.reshape(1, -1), 2)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(KNOWLEDGE):
            doc = KNOWLEDGE[idx]
            results.append(f"[{doc['topic']}] {doc['content']} (相似度:{score:.3f})")
    return "\n---\n".join(results) if results else "未找到相关内容。"

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

# ========== 4. 构建图 ==========
def build_rag_agent():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")
    return graph.compile()

# ========== 5. 演示 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("demo2: 知识库检索 Agent（LangGraph + FAISS）")
    print("=" * 60)

    agent = build_rag_agent()

    for q in ["什么是RAG，原理是什么", "向量数据库有哪些选择"]:
        print(f"\n--- 问题: {q} ---")
        result = agent.invoke({"messages": [HumanMessage(content=q)]})
        print(f"[最终回答] {result['messages'][-1].content}")
