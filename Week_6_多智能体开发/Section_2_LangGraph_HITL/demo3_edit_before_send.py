"""
demo3: 人工编辑后再发送

HITL 不只是 approve / reject。
很多真实场景里，人会修改 Agent 生成的内容，然后流程继续发送修改后的版本。

运行方式：
    python demo3_edit_before_send.py
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ReplyState(TypedDict):
    customer_question: str
    draft_reply: str
    final_reply: str
    sent: bool


def generate_draft(state: ReplyState) -> dict:
    print("[生成草稿] Agent 先生成一版客服回复")
    draft = (
        "您好，我们已经收到您的问题。"
        "我们会尽快处理，请您耐心等待。"
    )
    return {"draft_reply": draft}


def human_edit(state: ReplyState) -> dict:
    print("[暂停] 需要人工审核并可修改回复")
    edited_reply = interrupt(
        {
            "question": "请审核这段回复，可以直接通过，也可以修改后继续。",
            "customer_question": state["customer_question"],
            "draft_reply": state["draft_reply"],
        }
    )
    return {"final_reply": edited_reply}


def send_reply(state: ReplyState) -> dict:
    print("[发送] 使用人工确认后的内容发送")
    return {"sent": True}


def build_graph():
    graph = StateGraph(ReplyState)

    graph.add_node("generate_draft", generate_draft)
    graph.add_node("human_edit", human_edit)
    graph.add_node("send_reply", send_reply)

    graph.add_edge(START, "generate_draft")
    graph.add_edge("generate_draft", "human_edit")
    graph.add_edge("human_edit", "send_reply")
    graph.add_edge("send_reply", END)

    return graph.compile(checkpointer=MemorySaver())


def run_demo() -> None:
    app = build_graph()
    config = {"configurable": {"thread_id": "edit-before-send"}}

    print("\n=== 第一次运行：生成草稿后暂停 ===")
    first_result = app.invoke(
        {
            "customer_question": "我已经等了两天，为什么还没有退款？",
            "draft_reply": "",
            "final_reply": "",
            "sent": False,
        },
        config=config,
    )
    print("需要人工审核：", first_result["__interrupt__"][0].value)

    human_version = (
        "您好，抱歉让您等待。我们已经查询到您的退款申请，"
        "预计将在 1 个工作日内原路退回。感谢您的耐心。"
    )

    print("\n=== 第二次运行：模拟人工修改后继续发送 ===")
    final_result = app.invoke(Command(resume=human_version), config=config)
    print("最终发送内容：", final_result["final_reply"])
    print("是否已发送：", final_result["sent"])


if __name__ == "__main__":
    run_demo()

