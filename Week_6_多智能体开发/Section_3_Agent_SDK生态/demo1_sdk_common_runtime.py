"""
demo1: Agent SDK 的共同骨架

这个 demo 不绑定任何具体 SDK。
它用最少代码演示所有 Agent SDK 背后的共同结构：

Agent = 角色说明 + 工具列表
Tool = 可被 Agent 调用的函数
Runner = 负责执行 Agent
Result = 最终输出

运行方式：
    python demo1_sdk_common_runtime.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[[str], str]


@dataclass
class Agent:
    name: str
    instructions: str
    tools: list[Tool]


@dataclass
class RunResult:
    tool_used: str
    output: str


class Runner:
    @staticmethod
    def run(agent: Agent, user_input: str) -> RunResult:
        print(f"[Runner] 启动 Agent：{agent.name}")
        print(f"[Runner] 用户输入：{user_input}")

        selected_tool = choose_tool(agent.tools, user_input)
        print(f"[Runner] 选择工具：{selected_tool.name}")

        output = selected_tool.handler(user_input)
        return RunResult(tool_used=selected_tool.name, output=output)


def choose_tool(tools: list[Tool], user_input: str) -> Tool:
    if "订单" in user_input or "退款" in user_input:
        return next(tool for tool in tools if tool.name == "order_lookup")
    return next(tool for tool in tools if tool.name == "knowledge_search")


def order_lookup(query: str) -> str:
    return f"订单工具已处理：{query}。建议查询订单状态和支付流水。"


def knowledge_search(query: str) -> str:
    return f"知识库工具已处理：{query}。建议返回产品说明或帮助文档。"


def run_demo() -> None:
    agent = Agent(
        name="customer_support_agent",
        instructions="你是客服 Agent，根据问题选择合适工具。",
        tools=[
            Tool("order_lookup", "查询订单和退款状态", order_lookup),
            Tool("knowledge_search", "查询帮助文档", knowledge_search),
        ],
    )

    cases = [
        "我的订单为什么还没有退款？",
        "这个系统支持哪些功能？",
    ]

    for case in cases:
        print("\n" + "=" * 70)
        result = Runner.run(agent, case)
        print(f"工具：{result.tool_used}")
        print(f"结果：{result.output}")


if __name__ == "__main__":
    run_demo()

