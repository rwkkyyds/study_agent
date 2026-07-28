"""
demo3: LangGraph 子图 subgraph 订单处理流程

这个 demo 演示为什么要用子图：
当一段流程会重复出现，或者本身比较复杂时，可以把它封装成一个小图。

运行方式：
    python demo3_subgraph_order_pipeline.py
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class OrderState(TypedDict):
    order_id: str
    amount: float
    inventory_ok: bool
    payment_ok: bool
    logs: Annotated[list[str], operator.add]
    result: str


def check_inventory(state: OrderState) -> dict:
    inventory_ok = state["amount"] <= 500
    status = "库存检查通过" if inventory_ok else "库存不足，需要人工确认"
    print(f"[子图-库存] {status}")
    return {"inventory_ok": inventory_ok, "logs": [status]}


def check_payment(state: OrderState) -> dict:
    payment_ok = state["amount"] > 0
    status = "支付检查通过" if payment_ok else "支付金额异常"
    print(f"[子图-支付] {status}")
    return {"payment_ok": payment_ok, "logs": [status]}


def build_check_subgraph():
    subgraph = StateGraph(OrderState)

    subgraph.add_node("check_inventory", check_inventory)
    subgraph.add_node("check_payment", check_payment)

    subgraph.add_edge(START, "check_inventory")
    subgraph.add_edge("check_inventory", "check_payment")
    subgraph.add_edge("check_payment", END)

    return subgraph.compile()


check_subgraph = build_check_subgraph()


def receive_order(state: OrderState) -> dict:
    print(f"[主图-入口] 收到订单：{state['order_id']}")
    return {"logs": [f"收到订单 {state['order_id']}，金额 {state['amount']}"]}


def run_check_subgraph(state: OrderState) -> dict:
    print("[主图] 进入订单检查子图")
    checked_state = check_subgraph.invoke(state)  # 子图：把一段独立流程当成主图里的一个步骤来用。
    new_logs = checked_state["logs"][len(state["logs"]):]
    return {
        "inventory_ok": checked_state["inventory_ok"],
        "payment_ok": checked_state["payment_ok"],
        "logs": new_logs,
    }


def finish_order(state: OrderState) -> dict:
    print("[主图-收尾] 根据检查结果生成最终状态")

    if state["inventory_ok"] and state["payment_ok"]:
        result = "订单可以继续发货"
    else:
        result = "订单需要人工处理"

    return {"result": result, "logs": [result]}


def build_main_graph():
    graph = StateGraph(OrderState)

    graph.add_node("receive_order", receive_order)
    graph.add_node("run_check_subgraph", run_check_subgraph)
    graph.add_node("finish_order", finish_order)

    graph.add_edge(START, "receive_order")
    graph.add_edge("receive_order", "run_check_subgraph")
    graph.add_edge("run_check_subgraph", "finish_order")
    graph.add_edge("finish_order", END)

    return graph.compile()


def run_demo() -> None:
    app = build_main_graph()
    result = app.invoke(
        {
            "order_id": "ORDER-20260726-001",
            "amount": 299.0,
            "inventory_ok": False,
            "payment_ok": False,
            "logs": [],
            "result": "",
        }
    )

    print("\n=== 订单处理日志 ===")
    for log in result["logs"]:
        print(f"- {log}")
    print("最终结果：", result["result"])


if __name__ == "__main__":
    run_demo()
