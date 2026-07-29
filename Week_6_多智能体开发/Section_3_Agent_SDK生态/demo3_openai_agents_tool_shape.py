"""
demo3: OpenAI Agents SDK 的 Agent / Tool 形态

这个 demo 使用真实 openai-agents 包。
为了避免卡在 API Key，本 demo 不调用远程模型，只展示：
1. 如何定义 tool
2. 如何把 tool 挂到 Agent 上
3. SDK 里的 Agent 对象长什么样

运行方式：
    python demo3_openai_agents_tool_shape.py
"""

from __future__ import annotations

from agents import Agent, function_tool


@function_tool
def calculate_refund(order_amount: float, refund_ratio: float) -> str:
    """计算退款金额。"""
    refund = order_amount * refund_ratio
    return f"可退款金额：{refund:.2f} 元"


@function_tool
def lookup_policy(topic: str) -> str:
    """查询客服政策。"""
    policies = {
        "refund": "100 元以下可自动退款，100 元以上需要人工审批。",
        "invoice": "发票通常在付款后 24 小时内开具。",
    }
    return policies.get(topic, "没有找到对应政策。")


def run_demo() -> None:
    agent = Agent(
        name="refund_assistant",
        instructions="你是退款客服助手，需要根据政策和订单金额给出建议。",
        tools=[calculate_refund, lookup_policy],
    )

    print("=== OpenAI Agents SDK Agent 定义 ===")
    print("Agent 名称：", agent.name)
    print("Agent 指令：", agent.instructions)
    print("工具数量：", len(agent.tools))

    for tool in agent.tools:
        print(f"- 工具：{tool.name}")

    print("\n注意：真实调用 Runner.run 时需要可用模型和 API Key。")
    print("本 demo 的重点是让你先看懂 SDK 如何声明 Agent 和 tools。")


if __name__ == "__main__":
    run_demo()

