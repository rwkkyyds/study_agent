"""
Demo1: LangGraph StateGraph 基础（无 LLM，纯逻辑）
功能：用 TypedDict 定义 State → 编写 Node → 添加 Edge → 编译运行
核心：理解 LangGraph 的四大要素：State、Node、Edge、Conditional Edge
依赖：langgraph（已安装）
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from typing import TypedDict, Literal #TypedDict 用于定义 State 结构，Literal 用于定义条件边的返回值类型
from langgraph.graph import StateGraph, START, END #StateGraph 是核心类，START 和 END 是特殊节点常量


# ========== 1. 定义 State（状态） ==========
# State 是图中流动的数据，所有 Node 都能读写
# 类似于"全局变量"，TypedDict 定义它的结构
class CalculatorState(TypedDict):
    """计算器状态"""
    expression: str          # 输入的表达式，如 "3 + 5"
    result: float            # 计算结果
    steps: list[str]         # 记录每一步的操作日志


# ========== 2. 定义 Node（节点） ==========
# Node 是处理函数：读取 State → 计算 → 返回 State 的更新部分
# 注意：Node 只需要返回要更新的字段，不用返回整个 State

def parse_expression(state: CalculatorState) -> dict:
    """节点1：解析表达式"""
    expression = state["expression"]
    print(f"  [Node: parse_expression] 解析: {expression}")

    # 简单解析：拆分数字和运算符
    parts = expression.split() # 例如 "3 + 5" → ["3", "+", "5"]
    return {
        "steps": state["steps"] + [f"解析表达式: {expression} → {parts}"]
    }

#[1]+[2]+[3] = [1, 2, 3] 这里的步骤日志记录了我们解析表达式的过程，方便后续查看整个计算流程。
def calculate(state: CalculatorState) -> dict:
    """节点2：执行计算"""
    expression = state["expression"]
    print(f"  [Node: calculate] 计算: {expression}")

    try:
        result = eval(expression, {"__builtins__": {}}, {}) # eval 作用是计算字符串表达式的值 第二个参数禁止访问内置函数，第三个参数禁止访问全局变量
        #eg: eval("3 + 5") → 8
        return {
            "result": result,
            "steps": state["steps"] + [f"计算结果: {expression} = {result}"] #这里的state["steps"]是上一个节点返回的steps列表，我们在这个基础上添加新的步骤日志
        }
    except Exception as e:
        return {
            "result": 0.0,
            "steps": state["steps"] + [f"计算错误: {e}"]
        }


def check_positive(state: CalculatorState) -> dict:
    """节点3a：结果为正数的处理"""
    print(f"  [Node: check_positive] 结果 {state['result']} 是正数")
    return {
        "steps": state["steps"] + [f"结果 {state['result']} > 0，标记为正数"]
    }


def check_negative(state: CalculatorState) -> dict:
    """节点3b：结果为负数的处理"""
    print(f"  [Node: check_negative] 结果 {state['result']} 是负数")
    return {
        "steps": state["steps"] + [f"结果 {state['result']} < 0，标记为负数"]
    }


def check_zero(state: CalculatorState) -> dict:
    """节点3c：结果为零的处理"""
    print(f"  [Node: check_zero] 结果为零")
    return {
        "steps": state["steps"] + [f"结果为 0"]
    }


# ========== 3. 定义 Conditional Edge（条件边） ==========
# 条件边根据 State 内容决定下一步走哪个节点
# 返回值是下一个节点的名称

def route_by_result(state: CalculatorState) -> Literal["positive", "negative", "zero"]:
    """条件路由：根据计算结果的正负，走不同分支"""
    result = state["result"]
    print(f"  [Conditional Edge] 判断结果: {result}")

    if result > 0:
        return "positive"
    elif result < 0:
        return "negative"
    else:
        return "zero"


# ========== 4. 构建图 ==========
def build_calculator_graph() -> StateGraph:
    """构建计算器图"""
    # 创建 StateGraph，传入 State 类型
    graph = StateGraph(CalculatorState)

    # 添加节点
    graph.add_node("parse", parse_expression)    # 节点名 → 处理函数
    graph.add_node("calculate", calculate)
    graph.add_node("positive", check_positive)
    graph.add_node("negative", check_negative)
    graph.add_node("zero", check_zero)

    # 添加边（定义执行顺序）
    graph.add_edge(START, "parse")               # START → parse
    graph.add_edge("parse", "calculate")         # parse → calculate

    # 添加条件边（根据结果走不同分支）
    graph.add_conditional_edges(
        "calculate",                              # 从哪个节点出发
        route_by_result,                          # 路由函数
        {                                         # 返回值 → 目标节点的映射
            "positive": "positive",
            "negative": "negative",
            "zero": "zero"
        }
    )

    # 所有分支都汇到 END
    graph.add_edge("positive", END)
    graph.add_edge("negative", END)
    graph.add_edge("zero", END)

    return graph


# ========== 5. 运行图 ==========
def run_graph(expression: str):
    """运行图并打印 State 流转过程"""
    print(f"\n{'=' * 60}")
    print(f"表达式: {expression}")
    print("=" * 60)

    graph = build_calculator_graph()
    compiled = graph.compile()  # 编译图

    # 初始 State
    initial_state: CalculatorState = {
        "expression": expression,
        "result": 0.0,
        "steps": []
    }

    # 运行图（invoke 会自动按边的顺序执行节点）
    final_state = compiled.invoke(initial_state)

    print(f"\n--- 最终 State ---")
    print(f"  表达式: {final_state['expression']}")
    print(f"  结果: {final_state['result']}")
    print(f"  步骤日志:")
    for i, step in enumerate(final_state["steps"], 1):
        print(f"    {i}. {step}")


# ========== 6. 展示图结构 ==========
def show_graph_structure():
    """展示图的结构信息"""
    print("=" * 60)
    print("【LangGraph StateGraph 结构解析】")
    print("=" * 60)

    print("""
    State（状态）:
      - CalculatorState: expression, result, steps
      - 所有 Node 都能读写 State
      - Node 只返回要更新的字段（自动合并）

    Node（节点）:
      - parse_expression: 解析表达式
      - calculate: 执行计算
      - check_positive / check_negative / check_zero: 分支处理

    Edge（边）:
      - START → parse → calculate（固定顺序）

    Conditional Edge（条件边）:
      - calculate → route_by_result → positive / negative / zero
      - 根据 result 的正负走不同分支

    执行流程:
      START
        ↓
      parse_expression    ← 读 expression，写 steps
        ↓
      calculate           ← 读 expression，写 result + steps
        ↓
      route_by_result     ← 读 result，返回 "positive"/"negative"/"zero"
       / | \
      /  |  \
    pos neg zero          ← 三个分支，各自更新 steps
      \  |  /
        ↓
       END
    """)


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        show_graph_structure()

        # 测试三个不同场景
        run_graph("3 + 5")       # 正数
        run_graph("2 - 10")      # 负数
        run_graph("0 * 999")     # 零

        print(f"\n{'=' * 60}")
        print("[OK] LangGraph StateGraph 基础 Demo 完成！")
        print("核心收获：")
        print("  1. StateGraph 用 TypedDict 定义流动的数据")
        print("  2. Node 是处理函数，读 State → 计算 → 返回更新")
        print("  3. Edge 定义固定执行顺序")
        print("  4. Conditional Edge 根据 State 内容动态路由")
        print("  5. START / END 是特殊的起止节点")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
