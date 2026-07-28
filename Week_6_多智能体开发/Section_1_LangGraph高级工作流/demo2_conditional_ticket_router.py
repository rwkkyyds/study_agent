"""
demo2: LangGraph 条件路由工单系统

这个 demo 演示真实业务里最常见的 Agent 流程：
先判断用户问题属于哪一类，再走对应处理节点。

运行方式：
    python demo2_conditional_ticket_router.py
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class TicketState(TypedDict):
    user_message: str
    route: str
    steps: Annotated[list[str], operator.add]
    reply: str


def classify_ticket(state: TicketState) -> dict:
    message = state["user_message"].lower()

    if "退款" in message or "支付" in message or "订单" in message:
        route = "payment"
    elif "报错" in message or "打不开" in message or "接口" in message:
        route = "tech"
    else:
        route = "human"

    print(f"[分类] 用户问题被分到：{route}")
    return {"route": route, "steps": [f"分类结果：{route}"]}


def route_ticket(state: TicketState) -> Literal["payment", "tech", "human"]:
    return state["route"]  # 条件路由：返回哪个字符串，LangGraph 就去哪个节点。


def handle_payment(state: TicketState) -> dict:
    print("[支付处理] 查询订单和支付状态")
    return {
        "steps": ["查询订单状态", "检查支付流水", "生成退款/支付处理建议"],
        "reply": "你的问题属于订单/支付类，请先确认订单号，然后进入支付处理流程。",
    }


def handle_tech(state: TicketState) -> dict:
    print("[技术处理] 收集错误信息并定位服务")
    return {
        "steps": ["收集报错信息", "查看服务日志", "判断是否需要开发介入"],
        "reply": "你的问题属于技术故障类，请提供报错截图、请求时间和接口地址。",
    }


def handle_human(state: TicketState) -> dict:
    print("[人工处理] 问题不明确，转人工")
    return {
        "steps": ["问题类型不明确", "转人工客服确认"],
        "reply": "这个问题需要人工进一步确认，我会把它转给人工客服。",
    }


def build_graph():
    graph = StateGraph(TicketState)

    graph.add_node("classify_ticket", classify_ticket)
    graph.add_node("payment", handle_payment)
    graph.add_node("tech", handle_tech)
    graph.add_node("human", handle_human)

    graph.add_edge(START, "classify_ticket")
    graph.add_conditional_edges(
        "classify_ticket",
        route_ticket,
        {
            "payment": "payment",
            "tech": "tech",
            "human": "human",
        },
    )
    graph.add_edge("payment", END)
    graph.add_edge("tech", END)
    graph.add_edge("human", END)

    return graph.compile()


def run_case(message: str) -> None:
    app = build_graph()
    result = app.invoke(
        {
            "user_message": message,
            "route": "",
            "steps": [],
            "reply": "",
        }
    )

    print("\n用户问题：", message)
    print("处理步骤：")
    for step in result["steps"]:
        print(f"- {step}")
    print("最终回复：", result["reply"])


def run_demo() -> None:
    cases = [
        "我刚才支付了，但是订单还显示未付款，能帮我看一下吗？",
        "我调用聊天接口一直报错，服务好像打不开。",
        "我想问一下你们这个系统怎么收费？",
    ]

    for case in cases:
        print("\n" + "=" * 70)
        run_case(case)


if __name__ == "__main__":
    run_demo()

