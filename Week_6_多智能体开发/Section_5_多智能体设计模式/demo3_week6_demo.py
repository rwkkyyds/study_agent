"""
demo3: 第6周综合 Demo —— 智能客服工单处理系统

整合第6周所有知识点：
    Section 1 LangGraph 高级工作流  → 条件路由 + 并行
    Section 2 HITL                 → 高风险工单暂停等人审
    Section 3 Agent SDK 生态        → Agent 定义方式
    Section 4 AutoGen/CrewAI        → 多 Agent 编排思路
    Section 5 设计模式 + 容错       → 流水线 + 重试降级

业务场景：客服工单系统
    用户提交工单 → 分类 Agent 判断类型
      → 普通工单：自动处理（技术/业务 Agent）
      → 高风险工单（退款>500）：interrupt 暂停，等人审批
        → 审批通过：执行退款
        → 审批拒绝：记录归档
      → 处理失败：自动重试，重试耗尽降级

为了零依赖可运行，这里用纯 Python 模拟 LangGraph 的图执行逻辑，
不安装 langgraph，但控制流和真实 LangGraph 完全对应。

运行方式：
    python demo3_week6_demo.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


# =====================================================================
# 第一部分：状态定义（对应 LangGraph 的 StateGraph）
# =====================================================================

class TicketType(str, Enum):
    TECH = "tech"        # 技术问题
    BUSINESS = "business"  # 业务问题
    REFUND_HIGH = "refund_high"  # 高额退款（需人审）


class TicketStatus(str, Enum):
    CLASSIFIED = "classified"
    PENDING_APPROVAL = "pending_approval"  # HITL 暂停点
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"
    DEGRADED = "degraded"  # 降级处理


@dataclass
class TicketState:
    """工单状态，对应 LangGraph 的 StateGraph 状态对象。

    每个节点读/写这个 state，整个流程靠它传递。
    """
    ticket_id: str
    content: str
    amount: float = 0.0
    ticket_type: TicketType | None = None
    status: TicketStatus = TicketStatus.CLASSIFIED
    approval_result: str = ""  # 人审结果：approved/rejected
    result: str = ""
    retry_count: int = 0
    log: list[str] = field(default_factory=list)

    def add_log(self, msg: str) -> None:
        entry = f"[{self.status.value}] {msg}"
        self.log.append(entry)
        print(f"  {entry}")


# =====================================================================
# 第二部分：节点函数（对应 LangGraph 的 Node）
# =====================================================================

def classify_node(state: TicketState) -> TicketState:
    """分类 Agent：判断工单类型。

    真实场景会调 LLM 分类，这里用规则模拟。
    """
    state.add_log(f"分类 Agent 分析：{state.content}")
    if "退款" in state.content and state.amount >= 500:
        state.ticket_type = TicketType.REFUND_HIGH
        state.add_log(f"判定为【高额退款】，金额={state.amount}，需人审")
    elif "退款" in state.content:
        state.ticket_type = TicketType.BUSINESS
        state.add_log(f"判定为【普通退款】，金额={state.amount}，自动处理")
    else:
        state.ticket_type = TicketType.TECH
        state.add_log("判定为【技术问题】")
    return state


def route_node(state: TicketState) -> str:
    """条件路由：根据工单类型决定走哪个分支。

    对应 LangGraph 的 conditional_edges。
    返回值是下一个节点名。
    """
    if state.ticket_type == TicketType.REFUND_HIGH:
        return "human_approval"  # 高额退款走人审
    elif state.ticket_type == TicketType.BUSINESS:
        return "process_business"
    else:
        return "process_tech"


def process_tech_node(state: TicketState) -> TicketState:
    """技术 Agent 处理技术问题。"""
    state.add_log(f"技术 Agent 处理：{state.content}")
    state.result = f"技术方案已给出：重启服务/检查配置"
    state.status = TicketStatus.PROCESSED
    return state


def process_business_node(state: TicketState) -> TicketState:
    """业务 Agent 处理普通退款。"""
    state.add_log(f"业务 Agent 处理退款，金额={state.amount}")
    # 模拟偶发失败（演示重试）
    state.retry_count += 1
    if state.retry_count < 2:
        state.add_log(f"支付接口异常（第{state.retry_count}次），准备重试")
        raise RuntimeError("支付接口超时")

    state.result = f"退款{state.amount}元已到账"
    state.status = TicketStatus.PROCESSED
    return state


def human_approval_node(state: TicketState) -> TicketState:
    """HITL 暂停点：高风险退款等人审。

    真实 LangGraph 用 interrupt() 暂停，等 Command(resume=...) 恢复。
    这里用状态标记模拟：设为 PENDING_APPROVAL，外部注入审批结果后继续。
    """
    state.status = TicketStatus.PENDING_APPROVAL
    state.add_log(f"高额退款{state.amount}元，暂停等待人审...")
    # 模拟人工审批（真实场景这里会 interrupt，下面模拟注入结果）
    print("  --- [模拟 HITL] 等待人工审批... ---")
    time.sleep(0.5)
    # 模拟人审结果注入（真实场景由 Command(resume="approved") 注入）
    state.approval_result = "approved"
    state.add_log(f"人审结果：{state.approval_result}")
    if state.approval_result == "approved":
        state.status = TicketStatus.APPROVED
    else:
        state.status = TicketStatus.REJECTED
    return state


def execute_refund_node(state: TicketState) -> TicketState:
    """审批通过后执行退款。"""
    state.add_log(f"执行退款{state.amount}元")
    state.result = f"退款{state.amount}元已执行到账"
    state.status = TicketStatus.PROCESSED
    return state


def degrade_node(state: TicketState) -> TicketState:
    """降级节点：处理失败后兜底。

    对应第3周 Section_6 的降级策略，多 Agent 场景同样需要。
    """
    state.add_log("处理失败，进入降级流程")
    state.result = "【降级】已记录工单，转人工跟进"
    state.status = TicketStatus.DEGRADED
    return state


# =====================================================================
# 第三部分：图执行引擎（模拟 LangGraph 的编译+运行）
# =====================================================================

class TicketGraph:
    """工单处理图：模拟 LangGraph 的 StateGraph 编译和执行。

    真实 LangGraph 用 graph.compile() + graph.invoke(state)，
    这里手动按节点顺序执行，控制流完全对应。
    """

    def run(self, state: TicketState) -> TicketState:
        """执行工单处理流程。"""
        print(f"\n{'='*60}")
        print(f"处理工单：{state.ticket_id} | {state.content}")
        print(f"{'='*60}")

        # 节点1：分类
        state = classify_node(state)

        # 条件路由（对应 conditional_edges）
        route_to = route_node(state)

        if route_to == "human_approval":
            # HITL 分支：人审 → 审批通过执行退款 / 拒绝归档
            state = human_approval_node(state)
            if state.status == TicketStatus.APPROVED:
                state = execute_refund_node(state)
            else:
                state.add_log("审批拒绝，工单归档")

        elif route_to == "process_business":
            # 业务分支：带重试的处理
            max_retries = 3
            while state.retry_count <= max_retries:
                try:
                    state = process_business_node(state)
                    break
                except RuntimeError as e:
                    if state.retry_count >= max_retries:
                        state = degrade_node(state)
                        break
                    state.add_log(f"重试中...（第{state.retry_count}次失败）")
                    time.sleep(0.1)

        elif route_to == "process_tech":
            # 技术分支
            state = process_tech_node(state)

        print(f"\n  最终状态：{state.status.value}")
        print(f"  处理结果：{state.result}")
        return state


# =====================================================================
# 第四部分：跑三个场景
# =====================================================================

def run_demo() -> None:
    graph = TicketGraph()

    # 场景1：技术问题 → 自动处理
    graph.run(TicketState(ticket_id="T001", content="系统登录不了"))

    # 场景2：普通退款 → 业务 Agent 处理（带重试）
    graph.run(TicketState(ticket_id="T002", content="申请退款", amount=100))

    # 场景3：高额退款 → HITL 人审 → 执行退款
    graph.run(TicketState(ticket_id="T003", content="紧急退款", amount=2000))

    print(f"\n{'='*60}")
    print("第6周综合 Demo 总结：")
    print("  1. 条件路由：分类后按类型走不同分支（Section 1）")
    print("  2. HITL：高额退款暂停等人审（Section 2）")
    print("  3. 多 Agent：分类/技术/业务/人审多个角色协作（Section 3+4）")
    print("  4. 容错：业务 Agent 失败自动重试，耗尽降级（Section 5）")


if __name__ == "__main__":
    run_demo()
