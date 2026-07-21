"""
Demo 4: 真实 LLM 调用 + Retriever 概念 + 统一 Runnable 接口
学习目标：
  1. 用 GLM API 真实调用 LLM，感受 Prompt | LLM | Parser 完整链路
  2. 理解 Retriever 是什么（这里是概念预演，真正的向量检索在 Section 4）
  3. 看到"统一接口"的实际表现：invoke / batch / stream
运行方式：python demo4_real_llm_retriever.py

GLM API 兼容 OpenAI 接口，所以 LangChain 用 ChatOpenAI 连接即可。
"""

import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

# ========== 初始化 GLM（通过 OpenAI 兼容接口） ==========
llm = ChatOpenAI(
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    model="glm-4-flash",
    temperature=0.7,
)


# ================================================================
# 第一部分：Prompt | LLM | Parser 完整链路（真实 LLM 调用）
# ================================================================
print("=" * 60)
print("【第一部分：真实 LLM 调用 — Prompt | GLM | Parser】")
print()

# 链1：StrOutputParser — 直接拿文本
explain_prompt = ChatPromptTemplate.from_messages([
    ("system", "用一句话解释概念，不超过30字"),
    ("human", "{concept}"),
])

explain_chain = explain_prompt | llm | StrOutputParser()

concepts = ["RAG", "Embedding", "向量数据库"]
print("  链1: Prompt | GLM | StrOutputParser")
for concept in concepts:
    result = explain_chain.invoke({"concept": concept})
    print(f"    {concept} -> {result}")
print()

# 链2：JsonOutputParser — 结构化输出
classify_prompt = ChatPromptTemplate.from_messages([
    ("system", """将以下技术概念分类，返回JSON格式：
{{"name": "概念名", "category": "分类", "difficulty": "难度1-5"}}"""),
    ("human", "{concept}"),
])

classify_chain = classify_prompt | llm | JsonOutputParser()

print("  链2: Prompt | GLM | JsonOutputParser")
test_concepts = ["FastAPI", "Docker", "Kubernetes"]
for concept in test_concepts:
    result = classify_chain.invoke({"concept": concept})
    print(f"    {concept} -> {result}")
print()


# ================================================================
# 第二部分：Retriever 概念演示
# ================================================================
print("=" * 60)
print("【第二部分：Retriever 是什么？】")
print("""
  Retriever = 检索器，根据用户问题找到相关文档片段

  在 RAG 系统中的位置：

  用户问题 -> [Retriever 检索相关文档] -> Prompt(问题+文档) -> LLM -> 回答

  类比：你问图书馆员一个问题
  - 没有 Retriever：LLM 凭记忆回答（可能编造）
  - 有 Retriever：先查书找到相关段落，再根据段落回答（有据可依）

  本 demo 用"关键词匹配"模拟 Retriever，真正的向量检索在 Section 4 学习。
""")
print()

# 模拟知识库（实际项目中是向量数据库中的文档块）
knowledge_base = [
    "FastAPI 是一个现代 Python Web 框架，基于 Starlette 和 Pydantic，支持异步处理。",
    "LangChain 是 LLM 应用开发框架，提供 Prompt、LLM、Parser、Retriever 等标准组件。",
    "RAG（检索增强生成）让 LLM 先检索相关文档，再基于文档生成回答，减少幻觉。",
    "Embedding 是将文本转换为向量的技术，语义相似的文本向量距离更近。",
    "向量数据库（如 Milvus、Chroma）专门存储和检索向量，是 RAG 系统的核心基础设施。",
    "Pydantic 用于数据校验，FastAPI 用它自动校验请求体和生成 API 文档。",
    "LCEL 是 LangChain 的链式表达语言，用管道符 | 串联组件。",
]


def simple_retriever(query: str) -> str:
    """
    简单检索器：关键词匹配（模拟 Retriever 行为）
    真实 Retriever 会用向量相似度检索，这里用关键词匹配演示概念。
    """
    results = []
    query_lower = query.lower()
    for doc in knowledge_base:
        # 简单关键词匹配
        if any(keyword in doc.lower() for keyword in query_lower.split()):
            results.append(doc)
    # 最多返回 3 条
    return "\n".join(results[:3]) if results else "未找到相关文档"


# 用 RunnableLambda 包装成 LCEL 组件
retriever = RunnableLambda(simple_retriever)

# 测试检索器
print("  测试检索器（输入问题 -> 返回相关文档）：")
test_queries = ["RAG 是什么", "FastAPI 有什么特点", "向量数据库的作用"]
for q in test_queries:
    docs = retriever.invoke(q)
    print(f"    问题: {q}")
    print(f"    检索到: {docs[:80]}...")
    print()


# ================================================================
# 第三部分：RAG 链 = Retriever + Prompt + LLM + Parser
# ================================================================
print("=" * 60)
print("【第三部分：RAG 链 = Retriever | Prompt | GLM | Parser】")
print()

rag_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个AI助手。根据以下参考资料回答问题。
如果资料中没有相关内容，就说"资料中未找到相关信息"。

参考资料：
{context}"""),
    ("human", "{question}"),
])

# RAG 链：检索器 | Prompt | LLM | Parser
# 数据流：question -> retriever(找文档) -> prompt(拼接问题+文档) -> llm(生成回答) -> parser(提取文本)
rag_chain = (
    {
        "context": retriever,              # 问题 -> 检索相关文档
        "question": RunnablePassthrough(),  # 问题原样传递
    }
    | rag_prompt
    | llm
    | StrOutputParser()
)

print("  RAG 链结构：retriever | prompt | llm | parser")
print()

rag_questions = [
    "什么是RAG？",
    "FastAPI 和 Pydantic 什么关系？",
    "LCEL 是什么？",
]

for q in rag_questions:
    answer = rag_chain.invoke(q)
    print(f"  Q: {q}")
    print(f"  A: {answer}")
    print()


# ================================================================
# 第四部分：统一接口演示 — invoke / batch / stream
# ================================================================
print("=" * 60)
print("【第四部分：统一接口 — invoke / batch / stream】")
print("""
  LangChain 所有组件（Prompt/LLM/Parser/Retriever）都实现 Runnable 接口：
    .invoke(input)   — 单次调用
    .batch(inputs)   — 批量调用（并发执行）
    .stream(input)   — 流式输出（token 逐个返回）

  这就是"统一接口"的含义：不管内部是 Prompt 模板还是 LLM 模型，
  调用方式完全一样，可以随意替换、自由组合。
""")
print()

# 1. invoke — 单次调用
print("  1) invoke — 单次调用")
result = explain_chain.invoke({"concept": "Agent"})
print(f"     explain_chain.invoke({{'concept': 'Agent'}}) -> {result}")
print()

# 2. batch — 批量调用
print("  2) batch — 批量调用（多个输入并发执行）")
batch_inputs = [
    {"concept": "FastAPI"},
    {"concept": "Docker"},
    {"concept": "Kubernetes"},
]
batch_results = explain_chain.batch(batch_inputs)
for inp, res in zip(batch_inputs, batch_results):
    print(f"     {inp['concept']} -> {res}")
print()

# 3. stream — 流式输出
print("  3) stream — 流式输出（token 逐个返回）")
print("     ", end="")
for chunk in explain_chain.stream({"concept": "LangChain"}):
    print(chunk, end="", flush=True)
print()
print()


# ================================================================
# 总结
# ================================================================
print("=" * 60)
print("【总结】")
print("""
  1. Retriever = 检索器，根据问题找到相关文档
     本 demo 用关键词匹配模拟，Section 4 用真正的向量检索

  2. RAG 链 = Retriever | Prompt | LLM | Parser
     question -> 检索文档 -> 拼接 prompt -> LLM 生成 -> 结构化输出

  3. 统一接口（Runnable）：
     所有组件都支持 .invoke() / .batch() / .stream()
     换组件不需要改调用方式，这就是"可自由组合"的底层基础

  4. GLM 通过 OpenAI 兼容接口接入 LangChain
     换成 GPT-4、Claude 只需改 ChatOpenAI 的参数
""")
