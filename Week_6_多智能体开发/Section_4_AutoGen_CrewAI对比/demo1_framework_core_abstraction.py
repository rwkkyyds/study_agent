"""
demo1: AutoGen 与 CrewAI 的核心抽象对比

这个 demo 不安装 AutoGen / CrewAI，用纯 Python dataclass 把两个框架
最核心的"编排骨架"抽出来放在一起，让你一眼看清它们的本质差异。

核心差异（记住这一句）：
    AutoGen = 对话驱动：多个 Agent 在一个会话里互相说话推进
    CrewAI  = 任务驱动：把目标拆成一串任务，按顺序分给不同角色

运行方式：
    python demo1_framework_core_abstraction.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


# =====================================================================
# 第一部分：AutoGen 的核心抽象（对话驱动）
# =====================================================================

@dataclass
class ConversableAgent:
    """AutoGen 的基本单位：一个会说话的角色。

    AutoGen 里每个 Agent 都能"发消息"和"收消息后回话"。
    协作靠的是多个 Agent 在一个会话里轮流说话。
    """
    name: str
    system_message: str
    reply: Callable[[str, str], str]  # reply(上一条消息, 发送者) -> 我的回复


@dataclass
class GroupChat:
    """AutoGen 的协作容器：把多个 Agent 拉进一个"群聊"。

    群聊的关键问题是：该轮到谁说话？
    AutoGen 用 speaker_selection_strategy 决定下一句谁接话。
    """
    agents: list[ConversableAgent]
    messages: list[str] = field(default_factory=list)
    # next_speaker: 决定下一句轮到哪个 Agent，AutoGen 支持 auto/manual/round_robin
    next_speaker: Callable[[list[ConversableAgent], int], ConversableAgent] | None = None

    def run(self, initiator: ConversableAgent, prompt: str, rounds: int = 4) -> str:
        """启动一段群聊。initiator 先开口，后面按 next_speaker 轮流接话。"""
        print(f"[AutoGen GroupChat] 启动，发起者={initiator.name}")
        self.messages.append(f"{initiator.name}: {prompt}")
        current_speaker = initiator
        last_msg = prompt

        for i in range(rounds):
            # 决定下一个说话者：没有策略就默认轮流
            if self.next_speaker:
                current_speaker = self.next_speaker(self.agents, i)
            else:
                current_speaker = self.agents[i % len(self.agents)]

            reply = current_speaker.reply(last_msg, current_speaker.name)
            self.messages.append(f"{current_speaker.name}: {reply}")
            print(f"  轮次 {i+1} [{current_speaker.name}] -> {reply}")
            last_msg = reply

        return last_msg


# =====================================================================
# 第二部分：CrewAI 的核心抽象（任务驱动）
# =====================================================================

@dataclass
class Task:
    """CrewAI 的基本单位：一个有明确产出的任务。

    CrewAI 里 Agent 是角色，Task 才是流转的单位。
    一个任务绑定一个 Agent，产出会传给下一个任务。
    """
    description: str
    expected_output: str
    agent_name: str  # 这个任务交给哪个角色做
    context_from: list[str] = field(default_factory=list)  # 依赖哪些前置任务的产出


@dataclass
class Crew:
    """CrewAI 的协作容器：一队人 + 一串任务，按依赖顺序跑。

    CrewAI 的核心是"任务流水线"：上一个任务做完，产出喂给下一个，
    像 IDE 里的 build pipeline，每一步都有明确交接物。
    """
    tasks: list[Task]
    # role_handlers: 角色名 -> 处理函数，每个角色用自己的方式完成任务
    role_handlers: dict[str, Callable[[str, str], str]]

    def kickoff(self, user_goal: str) -> str:
        """CrewAI 的入口函数就叫 kickoff，这里模拟任务串行执行。"""
        print(f"[CrewAI kickoff] 目标={user_goal}")
        outputs: dict[str, str] = {"__goal__": user_goal}

        for task in self.tasks:
            # 拼接前置任务的产出作为上下文
            context = "\n".join(
                outputs.get(prev, "") for prev in task.context_from
            )
            handler = self.role_handlers[task.agent_name]
            result = handler(task.description, context)
            outputs[task.description] = result
            print(f"  任务 [{task.agent_name}] {task.description} -> {result}")

        # 最后一个任务的产出就是最终结果
        return outputs[self.tasks[-1].description]


# =====================================================================
# 第三部分：跑同一个目标，对比两种编排
# =====================================================================

def autogen_researcher(msg: str, speaker: str) -> str:
    return f"研究员：基于「{msg}」整理了3条要点"


def autogen_critic(msg: str, speaker: str) -> str:
    return f"评审员：'{msg[:20]}...' 的第2条不够严谨，建议补充数据来源"


def autogen_summarizer(msg: str, speaker: str) -> str:
    return f"总结员：综合讨论，最终结论是「{msg[:15]}...」"


def crewai_researcher(desc: str, context: str) -> str:
    return "3条调研要点 + 数据来源"


def crewai_writer(desc: str, context: str) -> str:
    return f"基于「{context}」写成一段技术总结"


def crewai_reviewer(desc: str, context: str) -> str:
    return f"审核「{context[:15]}...」通过，发布"


def run_autogen_demo() -> None:
    print("\n" + "=" * 70)
    print("AutoGen 路线：对话驱动，三个 Agent 在群里轮流说话")
    print("=" * 70)
    agents = [
        ConversableAgent("researcher", "你是研究员", autogen_researcher),
        ConversableAgent("critic", "你是评审员", autogen_critic),
        ConversableAgent("summarizer", "你是总结员", autogen_summarizer),
    ]
    # round_robin 策略：按列表顺序轮流发言
    chat = GroupChat(agents)
    chat.run(agents[0], "调研多智能体框架的选型", rounds=4)


def run_crewai_demo() -> None:
    print("\n" + "=" * 70)
    print("CrewAI 路线：任务驱动，三个任务按依赖串成流水线")
    print("=" * 70)
    tasks = [
        Task("调研多智能体框架", "3条要点+数据来源", "researcher"),
        Task("撰写技术总结", "一段总结", "writer", context_from=["调研多智能体框架"]),
        Task("审核并发布", "审核结论", "reviewer", context_from=["撰写技术总结"]),
    ]
    crew = Crew(
        tasks=tasks,
        role_handlers={
            "researcher": crewai_researcher,
            "writer": crewai_writer,
            "reviewer": crewai_reviewer,
        },
    )
    crew.kickoff("产出一份多智能体框架选型报告")


def run_demo() -> None:
    run_autogen_demo()
    run_crewai_demo()
    print("\n" + "=" * 70)
    print("对比结论：")
    print("  AutoGen：Agent 之间互相说话推进，谁接话靠 speaker 策略")
    print("  CrewAI ：任务按依赖串行，上一个产出喂给下一个，像流水线")


if __name__ == "__main__":
    run_demo()
