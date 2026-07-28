"""
demo2: 客服退款 HITL 审批流程

这个 demo 更接近真实业务：
小额退款自动通过，大额退款暂停等待人工审批。

运行方式：
    python demo2_refund_approval_workflow.py
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class RefundState(TypedDict):
    order_id: str
    amount: float
    reason: str
    need_human: bool
    approved: bool
    result: str


def analyze_refund(state: RefundState) -> dict:
    print(f"[分析] 订单 {state['order_id']} 申请退款，金额 {state['amount']}")
    need_human = state["amount"] >= 100
    return {"need_human": need_human}


def route_refund(state: RefundState) -> Literal["auto_refund", "human_approval"]:
    if state["need_human"]:
        print("[路由] 大额退款，进入人工审批")
        return "human_approval"

    print("[路由] 小额退款，自动通过")
    return "auto_refund"


def auto_refund(state: RefundState) -> dict:
    print("[自动退款] 金额较小，系统自动处理")
    return {
        "approved": True,
        "result": f"订单 {state['order_id']} 已自动退款 {state['amount']} 元",
    }


def human_approval(state: RefundState) -> dict:
    print("[暂停] 需要客服主管审批")
    decision = interrupt(
        {
            "question": "是否批准这笔大额退款？",
            "order_id": state["order_id"],
            "amount": state["amount"],
            "reason": state["reason"],
            "suggested_options": ["approve", "reject"],
        }
    )

    approved = decision == "approve"
    return {"approved": approved}


def finish_refund(state: RefundState) -> dict:
    if state["approved"]:
        return {"result": f"订单 {state['order_id']} 退款已批准，金额 {state['amount']} 元"}
    return {"result": f"订单 {state['order_id']} 退款被拒绝"}


def build_graph():
    graph = StateGraph(RefundState)

    graph.add_node("analyze_refund", analyze_refund)
    graph.add_node("auto_refund", auto_refund)
    graph.add_node("human_approval", human_approval)
    graph.add_node("finish_refund", finish_refund)

    graph.add_edge(START, "analyze_refund")
    graph.add_conditional_edges(
        "analyze_refund",
        route_refund,
        {
            "auto_refund": "auto_refund",
            "human_approval": "human_approval",
        },
    )
    graph.add_edge("auto_refund", END)
    graph.add_edge("human_approval", "finish_refund")
    graph.add_edge("finish_refund", END)

    return graph.compile(checkpointer=MemorySaver())


def run_demo() -> None:
    app = build_graph()

    print("\n=== 场景1：小额退款，自动通过 ===")
    small_result = app.invoke(
        {
            "order_id": "ORDER-SMALL-001",
            "amount": 39.0,
            "reason": "用户重复购买",
            "need_human": False,
            "approved": False,
            "result": "",
        },
        config={"configurable": {"thread_id": "small-refund"}},
    )
    print("最终结果：", small_result["result"])

    print("\n=== 场景2：大额退款，暂停等待人工 ===")
    config = {"configurable": {"thread_id": "large-refund"}}
    first_result = app.invoke(
        {
            "order_id": "ORDER-LARGE-001",
            "amount": 399.0,
            "reason": "用户投诉服务不可用",
            "need_human": False,
            "approved": False,
            "result": "",
        },
        config=config,
    )
    print("暂停信息：", first_result["__interrupt__"][0].value)

    print("\n=== 模拟主管批准，流程继续 ===")
    final_result = app.invoke(Command(resume="approve"), config=config)
    print("最终结果：", final_result["result"])


if __name__ == "__main__":
    run_demo()

