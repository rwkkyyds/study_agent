"""
Demo 3: LCEL — LangChain Expression Language（链式表达式）
学习目标：用 | 管道符把 Prompt -> LLM -> Parser 串联成一条链
运行方式：python demo3_lcel_chain.py

核心概念：
LCEL 用 | 管道符把组件串联，类似 Unix shell 的管道：
  prompt | model | parser
  数据从左往右流动，每个组件处理后传给下一个
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field


# ========== LCEL 基础语法 ==========
print("=" * 60)
print("【LCEL 基础语法】")
print("""
  传统写法（手动调用）：
    messages = prompt.format_messages(topic="RAG")
    response = llm.invoke(messages)
    result = parser.parse(response.content)

  LCEL 写法（管道串联）：
    chain = prompt | llm | parser
    result = chain.invoke({"topic": "RAG"})

  | 管道符 = 数据从左流到右，每一步自动处理
""")
print()


# ========== 1. 构建一条简单链 ==========
print("=" * 60)
print("【示例1：Prompt | LLM | StrParser 简单链】")

# 定义模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "用一句话解释以下概念，不超过30字"),
    ("human", "{concept}"),
])

# 注意：这里没有真正调用 LLM（避免需要 API Key）
# 演示 LCEL 的数据流动机制

# 模拟 LLM 的 Runnable（代替真实 LLM，方便无 Key 测试）
from langchain_core.runnables import RunnableLambda


def mock_llm(prompt_value):
    """模拟 LLM 响应（直接返回字符串，LCEL 下游 Parser 期望 str 输入）"""
    messages = prompt_value.to_messages()
    user_msg = messages[-1].content
    responses = {
        "RAG": "RAG是检索增强生成，让LLM先查资料再回答",
        "Agent": "Agent是能自主使用工具完成任务的AI系统",
        "Embedding": "Embedding是把文本转为数字向量的技术",
    }
    for key, val in responses.items():
        if key in user_msg:
            return val
    return f"这是关于'{user_msg}'的简要解释"


mock_llm_runnable = RunnableLambda(mock_llm)

# 用 LCEL 组装链
chain = prompt | mock_llm_runnable | StrOutputParser()

# 调用链
concepts = ["RAG", "Agent", "Embedding"]
for concept in concepts:
    result = chain.invoke({"concept": concept})
    print(f"  {concept} -> {result}")
print()


# ========== 2. 链的组合与复用 ==========
print("=" * 60)
print("【示例2：链的组合】")

# 翻译链
translate_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是翻译助手，将中文翻译为英文，只输出翻译结果"),
    ("human", "{text}"),
])


def mock_translate(prompt_value):
    messages = prompt_value.to_messages()
    user_msg = messages[-1].content
    translations = {
        "你好世界": "Hello World",
        "人工智能": "Artificial Intelligence",
        "机器学习": "Machine Learning",
    }
    return translations.get(user_msg, f"translated: {user_msg}")


translate_chain = translate_prompt | RunnableLambda(mock_translate) | StrOutputParser()

# 摘要链
summary_prompt = ChatPromptTemplate.from_messages([
    ("system", "将以下英文压缩为5个词以内的摘要"),
    ("human", "{text}"),
])


def mock_summary(prompt_value):
    messages = prompt_value.to_messages()
    user_msg = messages[-1].content
    return f"[摘要] {user_msg[:5]}"


summary_chain = summary_prompt | RunnableLambda(mock_summary) | StrOutputParser()

# 链的组合：翻译链的输出 -> 摘要链的输入
# 用 RunnablePassthrough 和 RunnableSequence 组合
from langchain_core.runnables import RunnablePassthrough

# 也可以用 pipe 串联两条链
combined = translate_chain | summary_chain

test_texts = ["你好世界", "人工智能", "机器学习"]
for text in test_texts:
    result = combined.invoke({"text": text})
    print(f"  '{text}' -> 翻译 -> 摘要 -> {result}")
print()


# ========== 3. 带 JsonOutputParser 的链 ==========
print("=" * 60)
print("【示例3：Prompt | MockLLM | JsonParser】")

json_prompt = ChatPromptTemplate.from_messages([
    ("system", "将以下概念转为JSON格式，包含 name 和 definition 字段"),
    ("human", "{concept}"),
])


def mock_json_llm(prompt_value):
    messages = prompt_value.to_messages()
    user_msg = messages[-1].content
    import json
    data = {"name": user_msg, "definition": f"{user_msg}的定义"}
    return json.dumps(data, ensure_ascii=False)


json_chain = json_prompt | RunnableLambda(mock_json_llm) | JsonOutputParser()

result = json_chain.invoke({"concept": "向量数据库"})
print(f"  输入: '向量数据库'")
print(f"  输出: {result}")
print(f"  类型: {type(result)}")
print(f"  访问: result['name'] = {result['name']}")
print()


# ========== 4. LCEL 核心总结 ==========
print("=" * 60)
print("【LCEL 核心总结】")
print("""
  1. | 管道符把组件串联：prompt | llm | parser
  2. 每个组件实现 Runnable 接口（invoke / batch / stream）
  3. 链可以组合：chain_a | chain_b = 新链
  4. 数据自动流动，无需手动处理中间状态
  5. 支持 .invoke() .batch() .stream() 三种调用方式

  为什么重要？
  -> 后续 RAG 的检索链、Agent 的工具调用链都基于 LCEL 构建
  -> 理解 LCEL = 理解 LangChain 的编程范式
""")
