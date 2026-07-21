"""
Demo1: 工具定义基础（@tool 装饰器）
功能：定义多个工具 → 测试工具调用 → 理解 docstring 的作用
核心：@tool 装饰器将函数转为 Agent 可调用的工具，docstring 是决策依据
依赖：langchain-core（已有）
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import math
from langchain_core.tools import tool


# ========== 1. @tool 装饰器基础 ==========
# @tool 装饰器做了什么？
# 1. 将函数包装为 StructuredTool 对象
# 2. 从 docstring 提取工具描述（Agent 靠这个决定何时调用）
# 3. 从参数注解生成输入 schema（Agent 靠这个知道传什么参数）

@tool
def calculator(expression: str) -> str:
    """计算数学表达式。支持加减乘除、幂运算、开方等。
    输入示例: '2 + 3 * 4', 'sqrt(16)', '2 ** 10'
    """
    try:
        allowed = {k: v for k, v in math.__dict__.items() if not k.startswith("_")} #_安全的数学求值：只允许 math 模块中的函数 
        result = eval(expression, {"__builtins__": {}}, allowed) #eval作用是将字符串 expression 作为 Python 表达式进行求值，并返回结果。这里通过限制内置函数和允许的数学函数来确保安全性。
        return str(result) #返回值 eg: "14", "4.0", "1024"
    except Exception as e:
        return f"计算错误: {e}"


@tool
def text_length(text: str) -> str:
    """计算文本的字符数和单词数。"""
    chars = len(text)
    words = len(text.split())
    return f"字符数: {chars}, 单词数: {words}"


@tool
def reverse_text(text: str) -> str:
    """将文本反转。输入一段文字，返回反转后的结果。"""
    return text[::-1]


# ========== 2. 查看工具属性 ==========
def inspect_tool(tool_obj):
    """查看工具对象的内部结构"""
    print(f"  名称: {tool_obj.name}")
    print(f"  描述: {tool_obj.description}")
    print(f"  参数 schema: {tool_obj.args_schema.schema() if tool_obj.args_schema else 'None'}")


# ========== 3. 测试工具调用 ==========
def test_tools():
    """测试工具的直接调用（不经过 Agent）"""
    tools = [calculator, text_length, reverse_text]

    print("=" * 60)
    print("【工具列表】")
    print("=" * 60)
    for t in tools:
        print(f"\n工具: {t.name}")
        inspect_tool(t)

    print(f"\n{'=' * 60}")
    print("【直接调用测试】")
    print("=" * 60)

    # 直接调用工具（不需要 Agent）
    print(f"\n  calculator('2 + 3 * 4') = {calculator.invoke({'expression': '2 + 3 * 4'})}")
    print(f"  calculator('sqrt(144)') = {calculator.invoke({'expression': 'sqrt(144)'})}")
    print(f"  text_length('Hello World') = {text_length.invoke({'text': 'Hello World'})}")
    print(f"  reverse_text('Agent') = {reverse_text.invoke({'text': 'Agent'})}")


# ========== 4. docstring 的重要性 ==========
def docstring_demo():
    """展示 docstring 如何影响 Agent 的工具选择"""
    print(f"\n{'=' * 60}")
    print("【docstring 的作用】")
    print("=" * 60)

    print("""
    Agent 选择工具的依据是 docstring：

    @tool
    def calculator(expression: str) -> str:
        '''计算数学表达式。支持加减乘除、幂运算等。'''  ← Agent 读这个
        ...

    当用户问 "3+5等于多少？" 时：
    1. Agent 读取所有工具的 docstring
    2. 匹配到 calculator 的描述 "计算数学表达式"
    3. 决定调用 calculator，传入 expression="3+5"

    如果 docstring 写得不好：
    - "处理数据" → Agent 不知道什么时候用
    - "计算" → 太模糊，可能和其他工具混淆
    - "计算数学表达式。支持加减乘除、幂运算等。" → 清晰明确 ✓
    """)


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        test_tools()
        docstring_demo()
        print(f"\n{'=' * 60}")
        print("[OK] 工具定义基础 Demo 完成！")
        print("核心收获：")
        print("  1. @tool 装饰器将函数转为 StructuredTool 对象")
        print("  2. docstring 是 Agent 决策的核心依据")
        print("  3. 参数注解生成输入 schema，Agent 靠它传参")
        print("  4. 工具可以 .invoke() 直接调用，不需要经过 Agent")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
