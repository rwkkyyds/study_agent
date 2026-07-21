"""
Demo 2: Output Parsers — 输出解析
学习目标：把 LLM 的自由文本输出，解析为结构化数据
运行方式：python demo2_output_parser.py

核心问题：
LLM 返回的是纯文本字符串，但程序需要结构化数据（JSON、列表等）
Output Parser = 把"人话"变成"程序能用的数据"
"""

from langchain_core.output_parsers import (
    StrOutputParser,
    JsonOutputParser,
    CommaSeparatedListOutputParser,
)
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


# ========== 1. StrOutputParser — 最简单的解析器 ==========
# 原样返回 LLM 的文本输出，不做任何处理
print("=" * 60)
print("【StrOutputParser】")
print("  作用：直接拿 LLM 输出的原始文本")
print("  用途：聊天机器人、文案生成等不需要结构化的场景")
print()


# ========== 2. CommaSeparatedListOutputParser — 逗号分隔列表 ==========
# 让 LLM 输出逗号分隔的列表，然后自动解析为 Python list
list_parser = CommaSeparatedListOutputParser()

# get_format_instructions() 返回格式化指令，告诉 LLM 按什么格式输出
format_instructions = list_parser.get_format_instructions()
print("=" * 60)
print("【CommaSeparatedListOutputParser】")
print(f"  格式指令（会注入到 prompt 中）：\n  {format_instructions}")
print()

# 模拟 LLM 的输出（实际场景由 LLM 生成）
llm_output = "苹果, 香蕉, 橙子, 葡萄, 西瓜"
parsed = list_parser.parse(llm_output)
print(f"  LLM 原始输出: {llm_output}")
print(f"  解析后: {parsed}")
print(f"  类型: {type(parsed)}")
print(f"  访问第2个元素: {parsed[1]}")
print()


# ========== 3. JsonOutputParser — JSON 结构化解析 ==========
# 让 LLM 输出 JSON，自动解析为 Python dict
json_parser = JsonOutputParser()

format_instructions = json_parser.get_format_instructions()
print("=" * 60)
print("【JsonOutputParser】")
print(f"  格式指令：\n  {format_instructions[:200]}...")
print()

# 模拟 LLM 输出
llm_json_output = '{"name": "张三", "age": 25, "skills": ["Python", "FastAPI"]}'
parsed = json_parser.parse(llm_json_output)
print(f"  LLM 原始输出: {llm_json_output}")
print(f"  解析后: {parsed}")
print(f"  访问 skills: {parsed['skills']}")
print()


# ========== 4. PydanticOutputParser — 最强解析器 ==========
# 用 Pydantic 模型定义输出格式，LLM 必须按 schema 输出
# 这是生产环境中最常用的解析器，因为有严格的类型校验
from langchain_core.output_parsers import PydanticOutputParser


class MovieReview(BaseModel):
    """电影评价结构化输出"""
    title: str = Field(description="电影名称")
    rating: float = Field(description="评分，1-10分")
    summary: str = Field(description="一句话评价", max_length=100)
    recommend: bool = Field(description="是否推荐")

    model_config = {"extra": "forbid"}  # 禁止额外字段，LLM 输出多余字段会报错


pydantic_parser = PydanticOutputParser(pydantic_object=MovieReview)

format_instructions = pydantic_parser.get_format_instructions()
print("=" * 60)
print("【PydanticOutputParser】")
print(f"  Pydantic Schema 指令：\n  {format_instructions[:300]}...")
print()

# 模拟 LLM 输出
llm_pydantic_output = '{"title": "流浪地球2", "rating": 9.0, "summary": "中国科幻里程碑", "recommend": true}'
parsed = pydantic_parser.parse(llm_pydantic_output)
print(f"  LLM 原始输出: {llm_pydantic_output}")
print(f"  解析后类型: {type(parsed)}")
print(f"  电影名: {parsed.title}")
print(f"  评分: {parsed.rating}")
print(f"  推荐: {parsed.recommend}")
print(f"  校验通过: Pydantic 自动检查类型和约束")
print()


# ========== 5. 核心总结 ==========
print("=" * 60)
print("【Output Parser 核心总结】")
print("""
  Parser 类型            适用场景               输出类型
  ─────────────────────────────────────────────────────
  StrOutputParser        聊天/文案生成           str
  ListOutputParser       标签/关键词提取         list
  JsonOutputParser       通用结构化输出          dict
  PydanticOutputParser   严格 schema 校验       BaseModel
""")
print("关键：格式指令 (format_instructions) 必须注入到 prompt 中")
print("否则 LLM 不知道按什么格式输出，Parser 就解析失败")
