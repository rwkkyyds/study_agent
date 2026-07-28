"""
demo1: LangGraph 并行评审工作流

这个 demo 演示一个真实开发里很常见的场景：
一个需求进来后，不是只让一个 Agent 处理，而是让多个角色同时看。

运行方式：
    python demo1_parallel_review_workflow.py
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class ReviewState(TypedDict):
    task: str
    reports: Annotated[list[str], operator.add]  # operator.add：多个节点返回 reports 时，不覆盖，而是追加合并。
    final_summary: str


def receive_task(state: ReviewState) -> dict:
    print("[入口] 收到任务，准备分给不同角色并行评审")
    return {"reports": [f"任务：{state['task']}"]}


def product_review(state: ReviewState) -> dict:
    print("[产品评审] 看这个功能对用户有没有价值")
    return {
        "reports": [
            "产品视角：这个需求要先明确用户是谁，以及用户为什么需要这个功能。"
        ]
    }


def engineering_review(state: ReviewState) -> dict:
    print("[工程评审] 看实现成本和技术风险")
    return {
        "reports": [
            "工程视角：需要拆分 API、状态存储、异常处理，避免把流程写成一堆 if-else。"
        ]
    }


def risk_review(state: ReviewState) -> dict:
    print("[风险评审] 看上线后可能哪里出问题")
    return {
        "reports": [
            "风险视角：需要记录日志和监控指标，否则上线后很难判断问题发生在哪一步。"
        ]
    }


def merge_reviews(state: ReviewState) -> dict:
    print("[汇总] 把不同角色的意见合成一个结论")
    summary = "\n".join(f"- {item}" for item in state["reports"])
    return {"final_summary": summary}


def build_graph():
    graph = StateGraph(ReviewState)

    graph.add_node("receive_task", receive_task)
    graph.add_node("product_review", product_review)
    graph.add_node("engineering_review", engineering_review)
    graph.add_node("risk_review", risk_review)
    graph.add_node("merge_reviews", merge_reviews)

    graph.add_edge(START, "receive_task")
    graph.add_edge("receive_task", "product_review")
    graph.add_edge("receive_task", "engineering_review")
    graph.add_edge("receive_task", "risk_review")
    graph.add_edge(["product_review", "engineering_review", "risk_review"], "merge_reviews")
    graph.add_edge("merge_reviews", END)

    return graph.compile()


def run_demo() -> None:
    app = build_graph()
    result = app.invoke(
        {
            "task": "给 AI 客服系统增加一个自动总结用户问题的功能",
            "reports": [],
            "final_summary": "",
        }
    )

    print("\n=== 最终汇总 ===")
    print(result["final_summary"])


if __name__ == "__main__":
    run_demo()

