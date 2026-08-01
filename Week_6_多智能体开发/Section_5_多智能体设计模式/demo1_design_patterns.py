"""
demo1: 多智能体三种经典设计模式

同一个目标"处理一个客户工单"，分别用三种结构跑一遍，
看清每种模式的控制流差异。

三种模式：
    1. 分层（Hierarchical）：有 manager 统筹，向下分发任务
    2. 对等（Peer-to-Peer）：无中心，Agent 互相调用协商
    3. 流水线（Pipeline）：串行传递，上游产出喂下游

运行方式：
    python demo1_design_patterns.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Agent:
    """一个角色：名字 + 处理函数。

    handler(输入) -> 产出
    """
    name: str
    role: str
    handle: Callable[[str], str]


# =====================================================================
# 模式1：分层（Hierarchical）—— 有 manager 统筹
# =====================================================================

@dataclass
class HierarchicalSystem:
    """分层模式：一个 manager 负责分发，worker 只管干自己的活。

    控制流：manager 接收目标 → 判断分给谁 → worker 执行 → 汇总
    像公司：部门经理派活，组员只管自己那块。
    """
    manager: Agent
    workers: list[Agent]
    # router: manager 用它决定目标分给哪个 worker
    router: Callable[[str, list[Agent]], Agent]

    def run(self, goal: str) -> str:
        print(f"  [分层] manager={self.manager.name} 接收目标：{goal}")
        worker = self.router(goal, self.workers)
        print(f"  [分层] manager 分发给：{worker.name}")
        result = worker.handle(goal)
        summary = self.manager.handle(result)
        print(f"  [分层] manager 汇总产出：{summary}")
        return summary


# =====================================================================
# 模式2：对等（Peer-to-Peer）—— 无中心，互相调用
# =====================================================================

@dataclass
class PeerToPeerSystem:
    """对等模式：没有 manager，Agent 之间直接互相调用。

    控制流：一个 Agent 先发言 → 另一个回应 → 往复直到收敛
    像圆桌讨论：谁有信息谁发言，靠内容驱动推进。
    """
    agents: list[Agent]
    max_rounds: int = 5

    def run(self, topic: str) -> str:
        print(f"  [对等] 讨论主题：{topic}")
        current_msg = self.agents[0].handle(topic)
        print(f"  [对等] {self.agents[0].name} 开场：{current_msg}")

        for i in range(self.max_rounds):
            # 简单轮流：第 i 轮由 agents[(i+1) % len] 接话
            speaker = self.agents[(i + 1) % len(self.agents)]
            current_msg = speaker.handle(current_msg)
            print(f"  [对等] 轮次{i+1} [{speaker.name}] -> {current_msg}")

            # 收敛条件：输出里出现"达成一致"
            if "达成一致" in current_msg:
                print(f"  [对等] 检测到收敛，讨论结束。")
                return current_msg

        print(f"  [对等] 达到最大轮次，强制结束。")
        return current_msg


# =====================================================================
# 模式3：流水线（Pipeline）—— 串行传递，上游喂下游
# =====================================================================

@dataclass
class PipelineSystem:
    """流水线模式：Agent 按顺序串行，上一个产出喂给下一个。

    控制流：agent1 处理 → 产出 → agent2 处理 → 产出 → ...
    像工厂流水线：每道工序拿上道的半成品继续加工。
    """
    stages: list[Agent]

    def run(self, raw_input: str) -> str:
        print(f"  [流水线] 原始输入：{raw_input}")
        current = raw_input
        for stage in self.stages:
            current = stage.handle(current)
            print(f"  [流水线] [{stage.name}] 产出：{current}")
        return current


# =====================================================================
# 三种模式各自的角色实现
# =====================================================================

def make_hierarchical() -> HierarchicalSystem:
    """分层：manager 负责分类+汇总，两个 worker 各管一类工单。"""
    def manager_handle(msg: str) -> str:
        # manager 既做分类（分发前），也做汇总（worker 回来后）
        if "退款" in msg or "订单" in msg:
            return f"已分类为【订单类】"
        return f"已分类为【咨询类】"

    def order_worker(msg: str) -> str:
        return f"订单处理完成：{msg[:15]}... 退款已发起"

    def consult_worker(msg: str) -> str:
        return f"咨询已回复：{msg[:15]}... 参考帮助文档"

    def router(goal: str, workers: list[Agent]) -> Agent:
        if "退款" in goal or "订单" in goal:
            return workers[0]
        return workers[1]

    return HierarchicalSystem(
        manager=Agent("manager", "统筹", manager_handle),
        workers=[
            Agent("order_worker", "订单处理", order_worker),
            Agent("consult_worker", "咨询回复", consult_worker),
        ],
        router=router,
    )


def make_p2p() -> PeerToPeerSystem:
    """对等：技术、法务、业务三方讨论一个方案。"""
    def tech(msg: str) -> str:
        if "方案" in msg:
            return "技术：可行，需要2周开发"
        return "技术：同意，达成一致"

    def legal(msg: str) -> str:
        if "可行" in msg:
            return "法务：合规，无风险"
        return "法务：待技术确认"

    def business(msg: str) -> str:
        if "合规" in msg:
            return "业务：达成一致，可推进"
        return "业务：等法务意见"

    return PeerToPeerSystem(agents=[
        Agent("tech", "技术", tech),
        Agent("legal", "法务", legal),
        Agent("business", "业务", business),
    ])


def make_pipeline() -> PipelineSystem:
    """流水线：采集 → 清洗 → 分析 → 出报告。"""
    return PipelineSystem(stages=[
        Agent("collector", "数据采集", lambda x: f"采集到：{x}"),
        Agent("cleaner", "数据清洗", lambda x: x.replace("采集到：", "清洗后：") + "（去重）"),
        Agent("analyzer", "数据分析", lambda x: f"分析：{x} 结论=趋势上升"),
        Agent("reporter", "出报告", lambda x: f"报告：{x} 已发布"),
    ])


def run_demo() -> None:
    print("=" * 70)
    print("模式1：分层（Hierarchical）—— manager 统筹分发")
    print("=" * 70)
    h = make_hierarchical()
    h.run("客户要求退款，订单号12345")

    print("\n" + "=" * 70)
    print("模式2：对等（Peer-to-Peer）—— 三方圆桌讨论")
    print("=" * 70)
    p = make_p2p()
    p.run("讨论新功能上线方案")

    print("\n" + "=" * 70)
    print("模式3：流水线（Pipeline）—— 串行传递")
    print("=" * 70)
    pl = make_pipeline()
    pl.run("用户行为日志")

    print("\n" + "=" * 70)
    print("对比总结：")
    print("  分层  ：有中心，manager 控制分发和汇总，适合分级指挥")
    print("  对等  ：无中心，靠内容互相驱动，适合讨论协商")
    print("  流水线：固定顺序串行，上游喂下游，适合流程固定的业务")


if __name__ == "__main__":
    run_demo()
