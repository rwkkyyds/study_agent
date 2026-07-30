"""
demo3: CrewAI 任务驱动协作（轻量模拟）

这个 demo 把 demo1 里的 CrewAI 部分拆开细讲：
重点看任务怎么按依赖串成流水线，以及产出怎么交接。

CrewAI 的核心机制：
    1. Agent = 角色（role + goal + backstory + tools）
    2. Task = 任务（description + expected_output + 指定 agent + 可选 context）
    3. Crew = 一队人 + 一串任务，按 process 串行/并行
    4. kickoff = 启动入口，上一个任务产出喂给下一个
    5. context_from = 任务依赖，决定谁先谁后

和 AutoGen 的关键区别：
    AutoGen 靠"说话"推进，CrewAI 靠"任务依赖"推进。
    所以 CrewAI 的流程更可控、更像流水线，但少了"自由讨论"的弹性。

运行方式：
    python demo3_crewai_task_driven.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Agent:
    """CrewAI 的角色：有明确职责和目标，被任务调用。

    CrewAI 的 Agent 比 AutoGen 的更"静态"：它的角色是固定的，
    不会在会话里自由发言，只在被分配到任务时才干活。
    """
    name: str
    role: str  # 角色名，如"研究员"
    goal: str  # 这个角色的目标
    # execute(任务描述, 上下文) -> 产出
    execute: Callable[[str, str], str]


@dataclass
class Task:
    """CrewAI 的任务：流程里的一个环节。

    context_from 列出它依赖哪些前置任务的产出，
    CrewAI 据此决定执行顺序（拓扑排序）。
    """
    id: str
    description: str
    expected_output: str
    agent_name: str
    context_from: list[str] = field(default_factory=list)


@dataclass
class Crew:
    """CrewAI 的协作容器：一队 Agent + 一串 Task，按依赖顺序跑。

    process 默认是 sequential（串行），也支持 hierarchical（有 manager 统筹）。
    这里实现 sequential，最常见也最易懂。
    """
    agents: list[Agent]
    tasks: list[Task]
    process: str = "sequential"

    def kickoff(self, goal: str) -> str:
        print(f"[Crew kickoff] 目标={goal}，process={self.process}")
        by_name = {a.name: a for a in self.agents}
        outputs: dict[str, str] = {"__goal__": goal}

        # 按拓扑顺序执行：这里 tasks 已经按依赖排好，直接顺序跑
        for task in self.tasks:
            context_parts = [
                outputs.get(dep, "") for dep in task.context_from
            ]
            context = "\n".join(part for part in context_parts if part)
            agent = by_name[task.agent_name]
            print(f"  分配任务 [{task.agent_name}/{agent.role}] {task.description}")
            result = agent.execute(task.description, context)
            outputs[task.id] = result
            print(f"    产出：{result}")

        return outputs[self.tasks[-1].id]


# ---------------- 角色实现（每个角色怎么完成任务） ----------------

def researcher_execute(desc: str, context: str) -> str:
    return "调研结果：3个框架对比表 + 各自适用场景"


def writer_execute(desc: str, context: str) -> str:
    # 写手要把研究员的产出转成总结
    return f"技术总结：基于「{context[:20]}...」写成一段可发布摘要"


def reviewer_execute(desc: str, context: str) -> str:
    # 评审员审核写手的产出，通过则标记可发布
    return f"审核通过，结论：{context[:20]}... 已发布"


def run_demo() -> None:
    print("=" * 70)
    print("CrewAI 任务驱动：任务按依赖串成流水线，每个角色干完自己的环节")
    print("=" * 70)

    agents = [
        Agent("researcher", "研究员", "产出可靠的调研结论", researcher_execute),
        Agent("writer", "技术写手", "把调研结论写成可读的总结", writer_execute),
        Agent("reviewer", "评审员", "审核内容质量并决定是否发布", reviewer_execute),
    ]

    tasks = [
        Task("t1", "调研多智能体框架", "对比表+场景", "researcher"),
        Task("t2", "撰写技术总结", "一段可读摘要", "writer", context_from=["t1"]),
        Task("t3", "审核并发布", "发布结论", "reviewer", context_from=["t2"]),
    ]

    crew = Crew(agents=agents, tasks=tasks, process="sequential")
    final = crew.kickoff("产出一份多智能体框架选型报告")

    print(f"\n最终产出：{final}")
    print("\n本 demo 重点：")
    print("  1. Agent 是静态角色，只在被分配任务时干活")
    print("  2. Task 用 context_from 声明依赖，决定执行顺序")
    print("  3. 上一个任务产出喂给下一个，像流水线交接")


if __name__ == "__main__":
    run_demo()
