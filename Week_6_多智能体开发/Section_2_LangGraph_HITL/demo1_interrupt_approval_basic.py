"""
demo1: 最小可运行 HITL 审批流程

这个 demo 演示 LangGraph 真实 interrupt 用法：
流程执行到 approve_action 节点时会暂停，等待人工批准。

运行方式：
    python demo1_interrupt_approval_basic.py
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ApprovalState(TypedDict):
    task: str
    approved: bool
    result: str


def prepare_action(state: ApprovalState) -> dict:
    print("[准备] Agent 准备执行一个高风险动作")
    return {"result": f"准备执行：{state['task']}"}


def approve_action(state: ApprovalState) -> dict:
    print("[暂停] 需要人工确认后才能继续")
    decision = interrupt(
        {
            "question": "是否批准执行这个动作？",
            "task": state["task"],
            "suggested_options": ["approve", "reject"],
        }
    )  # interrupt：让图暂停，把问题交给人；恢复时这里会拿到人的输入。

    approved = decision == "approve"
    print(f"[恢复] 收到人工决定：{decision}")
    return {"approved": approved}


def execute_action(state: ApprovalState) -> dict:
    if state["approved"]:
        print("[执行] 人工已批准，开始执行")
        return {"result": f"已执行：{state['task']}"}

    print("[终止] 人工未批准，不执行")
    return {"result": f"已拒绝：{state['task']}"}


def build_graph():
    graph = StateGraph(ApprovalState)

    graph.add_node("prepare_action", prepare_action)
    graph.add_node("approve_action", approve_action)
    graph.add_node("execute_action", execute_action)

    graph.add_edge(START, "prepare_action")
    graph.add_edge("prepare_action", "approve_action")
    graph.add_edge("approve_action", "execute_action")
    graph.add_edge("execute_action", END)

    return graph.compile(checkpointer=MemorySaver())


def run_demo() -> None:
    app = build_graph()
    config = {"configurable": {"thread_id": "demo1-approval"}}

    print("\n=== 第一次运行：流程会暂停 ===")
    first_result = app.invoke(
        {
            "task": "删除一批过期用户数据",
            "approved": False,
            "result": "",
        },
        config=config,
    )
    print("暂停结果：", first_result["__interrupt__"][0].value)

    print("\n=== 第二次运行：模拟人工点击 approve，流程继续 ===")
    final_result = app.invoke(Command(resume="approve"), config=config)
    print("最终结果：", final_result["result"])


if __name__ == "__main__":
    run_demo()

