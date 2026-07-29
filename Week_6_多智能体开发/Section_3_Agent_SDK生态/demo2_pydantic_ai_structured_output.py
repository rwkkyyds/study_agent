"""
demo2: PydanticAI 结构化输出

这个 demo 使用真实 pydantic-ai 包。
重点不是模型聪不聪明，而是看 SDK 如何把输出约束成 Pydantic 模型。

运行方式：
    python demo2_pydantic_ai_structured_output.py
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel


class TicketAnalysis(BaseModel):
    category: str = Field(description="问题类型，例如 payment、tech、human")
    priority: int = Field(ge=1, le=5, description="优先级，1 最低，5 最高")
    next_action: str = Field(description="下一步处理建议")


def run_demo() -> None:
    model = TestModel(
        custom_output_args={
            "category": "payment",
            "priority": 4,
            "next_action": "查询订单状态，并确认是否需要人工退款审批。",
        }
    )  # TestModel 是 pydantic-ai 提供的测试模型，用来在无 API Key 时验证 Agent 结构。

    agent = Agent(
        model=model,
        output_type=TicketAnalysis,
        instructions="分析用户工单，输出结构化处理建议。",
    )

    result = agent.run_sync("用户说：我付款了但是订单显示未支付。")

    print("=== PydanticAI 结构化输出 ===")
    print("原始类型：", type(result.output))
    print("问题类型：", result.output.category)
    print("优先级：", result.output.priority)
    print("下一步：", result.output.next_action)


if __name__ == "__main__":
    run_demo()

