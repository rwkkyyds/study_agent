"""
Demo 1: Prompt Templates — 提示词模板
学习目标：理解模板化提示词的核心价值，掌握基本用法
运行方式：python demo1_prompt_template.py

核心概念：
Prompt Template = 把提示词中的"变量"抽出来，变成可复用的模板
就像 Python 的 f-string，但专门针对 LLM 提示词设计
"""

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage


# ========== 1. 最简单的 PromptTemplate（纯文本模板） ==========
# PromptTemplate 用于 text completion 模型（如 GPT-3.5-turbo-instruct）
simple_template = PromptTemplate.from_template(
    "你是一个{role}专家，请用{style}的方式解释{topic}"
)

# 用 .format() 填充变量
prompt = simple_template.format(role="AI", style="通俗易懂", topic="什么是RAG")
print("=" * 60)
print("【PromptTemplate 示例】")
print(prompt)



# ========== 2. ChatPromptTemplate（聊天模型专用） ==========
# 聊天模型（GPT-4、Claude）需要 System / Human / AI 多角色消息
# ChatPromptTemplate 就是为此设计的

chat_template = ChatPromptTemplate.from_messages([
    # SystemMessage: 设定 AI 的角色和行为规则
    ("system", "你是一个资深{domain}工程师，回答简洁、专业、有代码示例"),
    # HumanMessage: 用户的问题
    ("human", "{question}"),
])

# 填充变量，生成消息列表
messages = chat_template.format_messages(domain="Python", question="装饰器是什么？")
print("=" * 60)
print("【ChatPromptTemplate 示例】")
for msg in messages:
    print(f"  [{msg.__class__.__name__}] {msg.content}")
print()


# ========== 3. 带 Few-Shot 示例的模板 ==========
# Few-Shot = 给 LLM 几个"输入-输出"示例，让它学会你想要的格式
few_shot_template = ChatPromptTemplate.from_messages([
    ("system", "你是一个情感分析助手，根据用户输入判断情感，只输出：正面/负面/中性"),
    # 多组示例
    ("human", "这部电影太棒了！"),
    ("ai", "正面"),
    ("human", "服务态度很差"),
    ("ai", "负面"),
    ("human", "今天天气一般"),
    ("ai", "中性"),
    # 真正的用户输入
    ("human", "{input}"),
])

messages = few_shot_template.format_messages(input="这个产品质量还行吧")
print("=" * 60)
print("【Few-Shot 模板示例】")
for msg in messages:
    print(f"  [{msg.__class__.__name__}] {msg.content}")
print()


# ========== 4. 模板的复用价值 ==========
# 同一个模板，可以填充不同的变量，生成不同的提示词
print("=" * 60)
print("【模板复用演示】")

roles = [
    {"role": "后端开发", "style": "深入浅出", "topic": "数据库索引"},
    {"role": "产品经理", "style": "业务导向", "topic": "用户增长"},
    {"role": "算法工程师", "style": "数学严谨", "topic": "梯度下降"},
]

for params in roles:
    result = simple_template.format(**params)
    print(f"  -> {result[:50]}...")

print()
print("模板定义一次，复用 N 次 —— 这就是 Prompt Template 的核心价值")
print("在生产环境中，模板统一管理在配置文件/数据库中，方便迭代和 A/B 测试")
