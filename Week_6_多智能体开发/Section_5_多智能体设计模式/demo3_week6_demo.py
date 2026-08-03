"""
demo3: 第6周综合 Demo —— 智能客服工单处理系统
================================================

整合第6周所有知识点：
    Section 1 LangGraph 高级工作流  → 条件路由 + 并行
    Section 2 HITL                 → 高风险工单暂停等人审
    Section 3 Agent SDK 生态        → Agent 定义方式
    Section 4 AutoGen/CrewAI        → 多 Agent 编排思路
    Section 5 设计模式 + 容错       → 流水线 + 重试降级 + 熔断

业务场景：客服工单系统
    用户提交工单 → 分类 Agent 判断类型
      → 普通工单：自动处理（技术/业务 Agent）
      → 高风险工单（退款>500）：interrupt 暂停，等人审批
        → 审批通过：执行退款
        → 审批拒绝：记录归档
      → 处理失败：自动重试，重试耗尽降级，连续失败熔断

====================================================================
整体架构速览（建议先看这里，再逐行看代码）
====================================================================

这个文件模拟了一个"多 Agent 智能客服系统"，用纯 Python 模拟
LangGraph 的图执行逻辑，控制流和真实 LangGraph 完全对应。

代码分成 4 大部分：

  【第一部分：状态定义】
    定义什么是"工单"（TicketState），包含工单ID、内容、金额、
    类型、状态、处理结果等，所有 Agent 节点都读写这个状态。

  【第二部分：节点函数】
    每个节点就是一个"Agent 要做的事"，比如：
    分类 Agent → 判断工单类型
    技术 Agent → 处理技术问题
    业务 Agent → 处理退款（带重试）
    人审 Agent → 等待人工审批
    熔断检查  → 连续失败太多就跳过
    降级处理  → 重试耗尽后兜底

  【第三部分：图执行引擎】
    负责按顺序执行节点，控制流程：
    分类 → 条件路由 → 技术/业务/人审 → 结果

  【第四部分：运行三个场景】
    分别演示三种不同工单的处理流程。

====================================================================
容错四层架构（和你刚才问的流程完全对应）
====================================================================

  超时层（第2层）→ 单次 Agent 执行有上限，防止卡死
  重试层（第3层）→ 失败后自动重试（最多3次）
  降级层（第4层）→ 重试耗尽后返回兜底结果
  熔断层（第1层）→ 连续失败触发，后续直接跳过

  执行顺序是：
    先检查熔断 → 再执行（带超时） → 失败后重试
    → 重试耗尽降级 → 降级结果返回 → 失败计数累积
    → 连续失败次数达到阈值 → 熔断器打开
    → 后续任务在调用前直接跳过该 Agent

====================================================================
运行方式：
    python demo3_week6_demo.py
====================================================================
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


# =====================================================================
# 第一部分：状态定义（对应 LangGraph 的 StateGraph）
# =====================================================================
# 这里定义的是"多 Agent 之间传递的数据结构"。
# 在真实 LangGraph 中，StateGraph 会维护一个状态对象，
# 每个节点（Node）读取、修改这个状态，再传给下一个节点。
# 这就是"图执行"的核心：数据流驱动控制流。

class TicketType(str, Enum):
    """工单类型枚举。

    分类 Agent 判断出工单属于哪种类型，然后路由到不同的处理分支。
    """
    TECH = "tech"          # 技术问题 → 走技术 Agent 处理
    BUSINESS = "business"  # 普通业务/退款 → 走业务 Agent 处理
    REFUND_HIGH = "refund_high"  # 高额退款（≥500元）→ 走人审流程


class TicketStatus(str, Enum):
    """工单状态枚举。

    每个状态代表工单在流程中的"位置"，节点根据状态决定下一步做什么。
    这其实就是"状态机"（State Machine），也是 LangGraph 的核心思想。
    """
    CLASSIFIED = "classified"            # 已分类，等待处理
    PENDING_APPROVAL = "pending_approval"  # 暂停等待人工审批（HITL 暂停点）
    APPROVED = "approved"                # 人审通过
    REJECTED = "rejected"                # 人审拒绝
    PROCESSED = "processed"              # 处理完成
    DEGRADED = "degraded"                # 降级处理（兜底）


@dataclass
class TicketState:
    """工单状态对象。

    这个类就是"多 Agent 之间传递的共享状态"。
    在真实 LangGraph 中，StateGraph 会自动维护这个状态，
    每个节点函数都可以读取和修改它。

    属性说明：
        ticket_id:    工单编号，唯一标识一个工单
        content:      工单内容，用户提交的问题描述
        amount:       涉及金额，退款类工单需要
        ticket_type:  分类结果，由分类 Agent 填写
        status:       当前状态，流程控制靠它
        approval_result: 人审结果，"approved" 或 "rejected"
        result:       最终处理结果文本
        retry_count:  当前重试次数，用于重试逻辑
        log:          处理日志，记录每一步发生了什么
"""
    ticket_id: str
    content: str
    amount: float = 0.0
    ticket_type: TicketType | None = None
    status: TicketStatus = TicketStatus.CLASSIFIED
    approval_result: str = ""
    result: str = ""
    retry_count: int = 0
    force_fail: bool = False  # 强制失败（用于熔断测试）
    log: list[str] = field(default_factory=list)

    def add_log(self, msg: str) -> None:
        """添加日志并打印。
        所有节点都通过这个方法来记录执行过程。
        """
        entry = f"[{self.status.value}] {msg}"
        self.log.append(entry)
        print(f"  {entry}")


# =====================================================================
# 第二部分：节点函数（对应 LangGraph 的 Node）
# =====================================================================
# 每个节点函数就是一个"Agent 要做的事"。
# 在真实 LangGraph 中，每个节点就是图中的一个"步骤"，
# 图引擎会按顺序或条件执行这些节点。
#
# 重要：所有的节点函数都遵循同一个签名：
#     def node_name(state: TicketState) -> TicketState
# 即：读入当前状态，返回修改后的状态。
# 这就是"图执行"的标准模式。

def classify_node(state: TicketState) -> TicketState:
    """===== 【节点1：分类 Agent】 =====

    功能：判断工单属于哪种类型。

    业务逻辑：
        - 如果包含"退款"且金额≥500 → 高额退款，需人审
        - 如果包含"退款"且金额<500 → 普通退款，自动处理
        - 其他 → 技术问题

    对应 LangGraph 概念：
        这是图中的一个普通 Node，执行完就进入下一步。
        它不决定下一步去哪，那是路由节点的事。
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
    """===== 【节点2：条件路由（条件边）】 =====

    功能：根据分类结果，决定下一步走哪个分支。

    对应 LangGraph 概念：
        这就是"条件边"（conditional_edges）。
        普通 Node 返回的是修改后的状态，路由节点返回的是"下一个节点名"。
        图引擎根据返回值决定下一步执行哪个 Node。

    返回的字符串就是下一个要执行的节点函数名。
    """
    if state.ticket_type == TicketType.REFUND_HIGH:
        return "human_approval"  # 高额退款 → 走人审分支
    elif state.ticket_type == TicketType.BUSINESS:
        return "process_business"  # 普通退款 → 走业务 Agent
    else:
        return "process_tech"  # 技术问题 → 走技术 Agent


def process_tech_node(state: TicketState) -> TicketState:
    """===== 【节点3：技术 Agent】 =====

    处理技术类工单。这个 Agent 比较简单，没有失败场景。
    """
    state.add_log(f"技术 Agent 处理：{state.content}")
    state.result = f"技术方案已给出：重启服务/检查配置"
    state.status = TicketStatus.PROCESSED
    return state


def process_business_node(state: TicketState) -> TicketState:
    """===== 【节点4：业务 Agent】（带重试） =====

    处理普通退款。这个 Agent 会模拟"偶发失败"来演示重试机制。

    重试机制对应你刚才问的"第3层"：
        - 第1次调用：故意失败，抛异常
        - 第2次调用：成功
        - 如果连续失败超过上限，会触发降级

    注意：这里只是"抛出异常"让上层处理重试，
    真正的重试逻辑在 TicketGraph.run() 中实现。

    特殊行为：
        - 如果 force_fail=True，则持续失败（用于熔断测试）
        - 否则，第1次失败，第2次成功（模拟偶发故障）
    """
    state.add_log(f"业务 Agent 处理退款，金额={state.amount}")
    state.retry_count += 1

    # 熔断测试模式：持续失败，模拟 Agent 完全不可用
    if state.force_fail:
        state.add_log(f"业务 Agent 持续不可用（第{state.retry_count}次调用）")
        raise RuntimeError("业务接口持续异常")

    # 正常模式：模拟偶发失败（第1次调用故意失败，验证重试机制）
    if state.retry_count < 2:
        state.add_log(f"支付接口异常（第{state.retry_count}次），准备重试")
        raise RuntimeError("支付接口超时")

    state.result = f"退款{state.amount}元已到账"
    state.status = TicketStatus.PROCESSED
    return state


def human_approval_node(state: TicketState) -> TicketState:
    """===== 【节点5：人审 Agent】（HITL 暂停点） =====

    对应 LangGraph 的 HITL（Human In The Loop）机制。
    当高风险工单需要人工审批时，流程会暂停在这里，
    等待人工输入审批结果后再继续。

    真实 LangGraph 中的流程：
        1. interrupt() 暂停图执行
        2. 返回 PENDING 状态给前端
        3. 人工审批后，Command(resume="approved") 恢复执行
        4. 图从暂停点继续

    这里用 time.sleep + 模拟注入结果来演示这个流程。
    """
    state.status = TicketStatus.PENDING_APPROVAL
    state.add_log(f"高额退款{state.amount}元，暂停等待人审...")
    # 模拟人工审批（真实场景这里会 interrupt，等待外部输入）
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
    """===== 【节点6：执行退款】 =====

    人审通过后，执行实际的退款操作。
    """
    state.add_log(f"执行退款{state.amount}元")
    state.result = f"退款{state.amount}元已执行到账"
    state.status = TicketStatus.PROCESSED
    return state


def degrade_node(state: TicketState) -> TicketState:
    """===== 【节点7：降级 Agent】（第4层） =====

    对应你刚才问的"第4层：降级"。
    当重试耗尽后，不报错中断流程，而是返回一个兜底结果。
    这样下游可以继续处理，不会因为单点故障而整个流程崩溃。

    什么是降级？
        降级是指"系统以较低质量继续运行"。
        比如这里本来应该自动退款，但系统不可用，就转为"记录工单转人工"。
        客户可能需要等更久，但系统不会崩溃。

    降级和熔断的区别：
        降级：这次任务失败了，我返回一个"不那么好但能用"的结果
        熔断：这个 Agent 可能坏了，后面的任务我不再调用它了
    """
    state.add_log("处理失败，进入降级流程")
    state.result = "【降级】已记录工单，转人工跟进"
    state.status = TicketStatus.DEGRADED
    return state


# =====================================================================
# 第三部分：图执行引擎（模拟 LangGraph 的编译+运行）
# =====================================================================
# 这部分是整个系统的"大脑"——它负责控制流程，把各个节点串起来。
#
# 在真实 LangGraph 中，你只需要：
#     graph = StateGraph(TicketState)  # 创建图
#     graph.add_node("classify", classify_node)  # 添加节点
#     graph.add_conditional_edges(...)  # 添加条件边
#     app = graph.compile()  # 编译
#     result = app.invoke(state)  # 执行
#
# 这里用纯 Python 手动模拟同样的流程控制逻辑。

class CircuitBreaker:
    """===== 熔断器（第1层） =====

    对应你刚才问的"第1层：熔断"。
    熔断器的核心思想是：如果某个 Agent 连续失败太多次，
    说明它可能已经坏了，后续请求不再真正调用它，
    而是直接失败或走降级，让系统"快速失败"而不是"卡死等超时"。

    熔断器的三个状态：
        CLOSED（关闭）  ：正常状态，允许调用
        OPEN（打开）    ：熔断状态，直接跳过，不调用
        HALF_OPEN（半开）：等待一段时间后，放一个请求探测是否恢复

    熔断和重试的关系：
        重试是"这次失败了，我再试一次"
        熔断是"已经失败很多次了，这个 Agent 可能坏了，别试了"
        所以熔断是比重试更高层级的保护机制。
    """

    # 熔断器状态常量
    CLOSED = "closed"          # 关闭：正常调用
    OPEN = "open"              # 打开：直接跳过
    HALF_OPEN = "half_open"    # 半开：试探性恢复

    def __init__(self, name: str, threshold: int = 3, recovery_timeout: float = 30.0):
        self.name = name                       # 被保护的 Agent 名称
        self.threshold = threshold             # 连续失败多少次后打开熔断
        self.recovery_timeout = recovery_timeout  # 熔断后多久尝试恢复
        self.failure_count = 0                 # 当前连续失败计数
        self.state = self.CLOSED               # 初始状态：关闭
        self.last_failure_time = 0.0           # 上次失败的时间戳

    def check(self) -> bool:
        """检查当前是否允许调用。

        返回 True 表示可以调用，False 表示熔断打开，直接跳过。
        这就是"调用前先检查熔断"。
        """
        if self.state == self.CLOSED:
            # 关闭状态：正常调用
            return True

        if self.state == self.OPEN:
            # 打开状态：检查是否过了恢复时间
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                # 恢复时间已到，转为半开状态，允许一次试探
                self.state = self.HALF_OPEN
                print(f"  [熔断器] {self.name} 冷却期结束，转为半开状态，允许探测")
                return True
            # 恢复时间还没到，直接跳过
            print(f"  [熔断器] {self.name} 熔断打开中，跳过调用")
            return False

        if self.state == self.HALF_OPEN:
            # 半开状态：允许这次调用（探测请求）
            return True

        return True

    def record_success(self):
        """记录一次成功调用。
        成功时重置失败计数，恢复为关闭状态。
        """
        self.failure_count = 0
        self.state = self.CLOSED
        print(f"  [熔断器] {self.name} 调用成功，重置失败计数，恢复关闭状态")

    def record_failure(self):
        """记录一次失败调用。
        如果连续失败次数达到阈值，打开熔断器。
        """
        self.failure_count += 1
        self.last_failure_time = time.time()
        print(f"  [熔断器] {self.name} 记录失败（连续{self.failure_count}次）")
        if self.failure_count >= self.threshold:
            self.state = self.OPEN
            print(f"  [熔断器] {self.name} 连续失败达到{self.threshold}次，熔断打开！")


class TicketGraph:
    """工单处理图引擎。

    模拟 LangGraph 的 StateGraph + compile + invoke。
    真实 LangGraph 会自动管理状态传递和条件路由，
    这里手动实现同样的控制流，并加入重试/降级/熔断逻辑。

    这是整个系统的"运行时"（Runtime），负责：
        1. 按顺序执行节点
        2. 条件路由（根据类型走不同分支）
        3. 重试机制（第3层）
        4. 降级机制（第4层）
        5. 熔断保护（第1层）
    """

    def __init__(self):
        """初始化时创建熔断器。

        每个 Agent 类型都有自己的熔断器，独立计数。
        这样当一个 Agent 熔断时，不影响其他 Agent。
        """
        # 为每个可能出错的 Agent 创建独立的熔断器
        self.circuit_breakers = {
            "business": CircuitBreaker("业务 Agent", threshold=3, recovery_timeout=5),
            "tech": CircuitBreaker("技术 Agent", threshold=3, recovery_timeout=5),
        }

    def run(self, state: TicketState) -> TicketState:
        """执行工单处理流程（主流程）。

        这个方法的执行流程对应你刚才理解的"多层容错"：

        1. 分类 Agent 判断类型 ← 无容错，分类不会失败
        2. 条件路由决定走哪个分支
        3. 技术分支：简单的单次调用
        4. 业务分支：带重试+降级+熔断
        5. 人审分支：HITL 暂停审批
        """
        print(f"\n{'='*60}")
        print(f"处理工单：{state.ticket_id} | {state.content}")
        print(f"{'='*60}")

        # ---- 第一步：分类节点 ----
        # 分类比较简单，不会失败，所以不需要容错
        state = classify_node(state)

        # ---- 第二步：条件路由 ----
        route_to = route_node(state)

        if route_to == "human_approval":
            # ===== HITL 分支：人审流程 =====
            # 人审本身不涉及重试/熔断，因为是人做决策
            # 但人审可能超时（等待太久），这里简化处理
            state = human_approval_node(state)
            if state.status == TicketStatus.APPROVED:
                state = execute_refund_node(state)
            else:
                state.add_log("审批拒绝，工单归档")

        elif route_to == "process整的四层容错 =====
            # 这是最复杂的_business":
            # ===== 业务分支：带完场景，演示了：
            #   第1层（熔断）：调用前检查熔断器
            #   第2层（超时）：单次调用有超时限制
            #   第3层（重试）：失败后指数退避重试
            #   第4层（降级）：重试耗尽后兜底
            state = self._execute_with_resilience(
                state=state,
                agent_name="business",
                agent_func=process_business_node,
                max_retries=3,
                timeout_per_call=2.0,
            )

        elif route_to == "process_tech":
            # ===== 技术分支：简单处理，也带熔断保护 =====
            # 技术 Agent 在这个 Demo 中不会失败，
            # 但真实场景中也可能失败，所以也带熔断保护
            state = self._execute_with_resilience(
                state=state,
                agent_name="tech",
                agent_func=process_tech_node,
                max_retries=2,
                timeout_per_call=2.0,
            )

        print(f"\n  最终状态：{state.status.value}")
        print(f"  处理结果：{state.result}")
        return state

    def _execute_with_resilience(
        self,
        state: TicketState,
        agent_name: str,
        agent_func: callable,
        max_retries: int = 3,
        timeout_per_call: float = 5.0,
    ) -> TicketState:
        """带四层容错的 Agent 执行器。

        这是整个 Demo 中最重要的方法，它实现了你刚才问的完整流程：

        执行顺序：
            ┌──────────────────────────────────────────────┐
            │  ① 检查熔断器                                  │
            │    ├─ 熔断打开 → 直接降级，不调用 Agent         │
            │    └─ 熔断关闭 → 继续                           │
            │                                                │
            │  ② 执行 Agent 调用（带超时保护）                 │
            │    ├─ 成功 → 记录成功，重置熔断计数              │
            │    └─ 超时/异常 → 进入重试                     │
            │                                                │
            │  ③ 重试循环（最多 max_retries 次）              │
            │    ├─ 成功 → 结束                                 │
            │    └─ 重试耗尽 → 进入降级                       │
            │                                                │
            │  ④ 降级处理                                     │
            │    └─ 返回兜底结果，不阻塞流程                   │
            │                                                │
            │  ⑤ 失败计数 → 熔断器统计（下一次调用生效）       │
            └──────────────────────────────────────────────┘

        参数：
            state:          当前工单状态
            agent_name:     Agent 名称（用于熔断器查找）
            agent_func:     要执行的 Agent 函数
            max_retries:    最大重试次数（第3层）
            timeout_per_call: 单次调用超时秒数（第2层）
        """
        # ===== 第1层：熔断检查（调用前检查） =====
        # 熔断器如果在打开状态，根本不会调用 Agent，
        # 直接走降级，避免浪费时间和资源去等一个可能已经坏了的 Agent
        breaker = self.circuit_breakers.get(agent_name)
        if breaker and not breaker.check():
            # 熔断器打开，跳过 Agent 调用，直接降级
            state.add_log(f"熔断器打开，跳过{agent_name}，直接降级")
            state = degrade_node(state)
            return state

        # ===== 第2层 + 第3层：超时保护 + 重试循环 =====
        # 这里的重试实现了"指数退避"策略：
        #   第1次重试等待：0.5秒
        #   第2次重试等待：1.0秒
        #   第3次重试等待：2.0秒
        # 每次等待时间翻倍，避免频繁重试加重系统负担
        last_exception = None
        for attempt in range(max_retries + 1):  # 第1次是原始调用，后面是重试
            try:
                # ===== 第2层：超时保护 =====
                # 用 time.time() 模拟超时检测。
                # 真实场景中，调用 LLM 或外部 API 时，
                # 会用 timeout 参数或 asyncio.wait_for 来限制等待时间。
                start_time = time.time()
                state = agent_func(state)
                elapsed = time.time() - start_time
                state.add_log(f"调用成功，耗时{elapsed:.2f}秒")

                # 调用成功，记录成功，重置熔断计数
                if breaker:
                    breaker.record_success()
                return state

            except Exception as e:
                elapsed = time.time() - start_time
                last_exception = e
                state.add_log(f"调用失败（{type(e).__name__}），耗时{elapsed:.2f}秒")

                if attempt < max_retries:
                    # ===== 第3层：重试（指数退避） =====
                    # 还有重试次数，等待一段时间后重试
                    # 等待时间 = 基础等待 × 2^attempt
                    wait_time = 0.5 * (2 ** attempt)
                    state.add_log(f"等待{wait_time:.1f}秒后第{attempt + 1}次重试...")
                    time.sleep(wait_time)
                # 如果重试耗尽，循环结束，进入降级

        # ===== 第4层：降级（重试耗尽后） =====
        # 重试全部失败，不报错，而是返回一个兜底结果
        # 这就是"降级"：系统以较低质量继续运行
        state.add_log(f"重试{max_retries}次全部失败，进入降级")
        state = degrade_node(state)

        # ===== 熔断统计（为下一次调用做准备） =====
        # 记录这次失败，如果连续失败次数达到阈值，熔断器打开
        # 注意：熔断不是立即阻止本次调用，而是阻止下一次调用
        if breaker:
            breaker.record_failure()

        return state


# =====================================================================
# 第四部分：跑三个场景
# =====================================================================
# 运行三个不同场景，分别演示不同分支。

def run_demo() -> None:
    """运行三个工单场景，展示不同处理流程。

    场景1：技术问题 → 技术 Agent → 自动处理
    场景2：普通退款 → 业务 Agent → 带重试 → 成功
    场景3：高额退款 → HITL 人审 → 审批通过 → 执行退款
    场景4：（额外）连续失败场景 → 演示熔断器如何工作
    """
    graph = TicketGraph()

    # ---- 场景1：技术问题 → 自动处理 ----
    print("\n" + "★" * 60)
    print("★ 场景1：技术问题，直接走技术 Agent 自动处理")
    print("★" * 60)
    graph.run(TicketState(ticket_id="T001", content="系统登录不了"))

    # ---- 场景2：普通退款 → 业务 Agent 处理（带重试） ----
    print("\n" + "★" * 60)
    print("★ 场景2：普通退款，业务 Agent 处理")
    print("★  (第1次失败，自动重试第2次成功)")
    print("★" * 60)
    graph.run(TicketState(ticket_id="T002", content="申请退款", amount=100))

    # ---- 场景3：高额退款 → HITL 人审 → 执行退款 ----
    print("\n" + "★" * 60)
    print("★ 场景3：高额退款，暂停等人审")
    print("★  (模拟人审通过，然后执行退款)")
    print("★" * 60)
    graph.run(TicketState(ticket_id="T003", content="紧急退款", amount=2000))

    # ---- 场景4：演示熔断器 ----
    # 连续创建多个失败的工单，触发熔断器打开
    # 当熔断器打开后，后续工单不再真正调用业务 Agent，直接降级
    print("\n" + "★" * 60)
    print("★ 场景4：演示熔断器")
    print("★  连续多次失败触发熔断，后续任务直接跳过不再调用")
    print("★" * 60)
    print("★  (注意对比：前3个工单会实际调用业务 Agent 并重试,")
    print("★   第4个工单熔断器已打开，直接跳过不再调用)")
    print("★" * 60)

    # 连续创建多个"永远失败"的业务工单，模拟业务 Agent 持续不可用
    # 金额=50 < 500，所以走业务分支（不是人审分支）
    # force_fail=True 让业务 Agent 每次都失败
    for i in range(4):
        print(f"\n  --- 熔断测试工单 #{i + 1} ---")
        graph.run(TicketState(
            ticket_id=f"F00{i + 1}",
            content="申请退款",
            amount=50,        # < 500，走业务分支
            force_fail=True,  # 强制业务 Agent 持续失败
        ))

    print(f"\n{'='*60}")
    print("第6周综合 Demo 总结：")
    print("  1. 条件路由：分类后按类型走不同分支（Section 1）")
    print("  2. HITL：高额退款暂停等人审（Section 2）")
    print("  3. 多 Agent：分类/技术/业务/人审多个角色协作（Section 3+4）")
    print("  4. 容错：业务 Agent 失败自动重试，耗尽降级（Section 5）")
    print("  5. 熔断：连续失败触发熔断，后续任务直接跳过（Section 5 新增）")


if __name__ == "__main__":
    run_demo()