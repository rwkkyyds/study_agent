"""
Demo2: ReAct Agent 完整推理循环
功能：定义工具 → 创建 ReAct Agent → 运行推理循环
核心：理解 Thought → Action → Observation 的循环推理过程
依赖：langchain-openai, langchain（已有）
注意：langchain 1.3.x 使用 create_agent 新 API（基于 langgraph）
前置：先运行 demo1_tool_basics.py 理解工具定义
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import math
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent


# ========== 配置 ==========
ZHIPU_API_KEY = "70041ddde9824461bfb02fac3f469fc3.pDZCoxOgkovIx1vT"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 1. 定义工具 ==========
# @tool 装饰器将普通函数转为 Agent 可调用的工具
# docstring 非常重要：Agent 根据它来决定何时调用这个工具

@tool
def calculator(expression: str) -> str:
    """计算数学表达式。支持加减乘除、幂运算、开方等。
    输入示例: "2 + 3 * 4", "sqrt(16)", "2 ** 10"
    """
    try:
        # 安全的数学求值：只允许 math 模块中的函数
        allowed = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        result = eval(expression, {"__builtins__": {}}, allowed)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


@tool
def knowledge_base(query: str) -> str:
    """查询内部知识库，获取技术文档、产品信息等。
    当用户问到技术概念（如 RAG、Agent、ReAct、Milvus）时使用此工具。
    """
    # 模拟知识库（生产环境中对接 RAG 或数据库）
    kb = {
        "rag": "RAG（检索增强生成）= 检索外部知识 + LLM 生成回答。核心组件：文档解析、向量化、向量库、检索、重排、生成。",
        "agent": "Agent = LLM（大脑）+ Tools（手脚）+ 推理循环。核心能力：自主决策调用哪个工具、按什么顺序调用。",
        "react": "ReAct = Reasoning + Acting。每一步：Thought（思考）→ Action（行动）→ Observation（观察），循环直到完成任务。",
        "milvus": "Milvus 是生产级向量数据库，支持十亿级向量检索，Docker 部署，HNSW 索引。",
        "langchain": "LangChain 是 LLM 应用开发框架，核心组件：Prompt Template、Output Parser、LCEL 链路、Agent、Tools。",
    }
    query_lower = query.lower()
    results = []
    for key, value in kb.items():
        if key in query_lower:
            results.append(value)
    if results:
        return "\n".join(results)
    return f"知识库中未找到与 '{query}' 相关的信息。"


@tool
def get_current_time() -> str:
    """获取当前日期和时间。当用户问'现在几点'、'今天几号'时使用。"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ========== 2. 创建 Agent ==========
def create_react_agent_demo():
    """
    创建 ReAct Agent（langchain 1.3.x 新 API）：
    - model：LLM（大脑）
    - tools：工具列表（手脚）
    - system_prompt：行为指导

    内部自动处理：
    - ReAct 推理循环（Thought → Action → Observation）
    - 工具调用解析
    - 循环终止条件（Agent 决定不再调用工具时停止）
    """
    # LLM（大脑）
    llm = ChatOpenAI(
        api_key=ZHIPU_API_KEY,
        base_url=ZHIPU_BASE_URL,
        model="glm-4-flash",
        temperature=0,
    )

    # 工具列表（手脚）
    tools = [calculator, knowledge_base, get_current_time]

    # System Prompt：指导 Agent 的行为模式
    system_prompt = (
        "你是一个智能助手，可以使用工具来回答问题。\n"
        "可用工具：计算器(calculator)、知识库查询(knowledge_base)、时间查询(get_current_time)\n\n"
        "请按以下步骤思考：\n"
        "1. 分析用户问题，判断是否需要调用工具\n"
        "2. 如果需要，选择合适的工具并调用\n"
        "3. 根据工具返回的结果，继续思考或给出最终回答\n"
        "4. 不要编造信息，该用工具时必须用工具"
    )

    # create_agent：一行代码创建完整的 ReAct Agent
    # 返回的是 CompiledStateGraph，可直接 invoke
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    return agent


# ========== 3. 运行测试 ==========
def run_demo():
    """运行 Agent Demo，展示 ReAct 推理过程"""
    agent = create_react_agent_demo()

    questions = [
        # 需要调用工具的问题
        "计算一下 (15 * 8 + 120) / 4 等于多少？",
        # 需要查询知识库的问题
        "什么是 RAG？它和 Agent 有什么区别？",
        # 需要组合多个工具的问题
        "现在几点了？另外帮我算一下 2 的 20 次方是多少？",
    ]

    for i, q in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"问题 {i+1}: {q}")
        print(f"{'=' * 60}")

        try:
            # invoke 传入消息列表，Agent 自动执行推理循环
            result = agent.invoke({"messages": [("human", q)]})
            # 最后一条消息是 Agent 的最终回答
            final_message = result["messages"][-1]
            print(f"\n[最终回答] {final_message.content}")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print("[OK] Agent Demo 完成！")
    print("核心收获：")
    print("  1. Agent = LLM + Tools + 推理循环")
    print("  2. ReAct：Thought → Action → Observation 循环")
    print("  3. @tool 装饰器定义工具，docstring 是 Agent 决策依据")
    print("  4. create_agent 一行代码创建完整 Agent")


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        run_demo()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback # 打印完整错误堆栈，方便调试
        traceback.print_exc()
