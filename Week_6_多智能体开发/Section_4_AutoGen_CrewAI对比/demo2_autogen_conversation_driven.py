"""
demo2: AutoGen 对话驱动协作（轻量模拟）

这个 demo 把 demo1 里的 AutoGen 部分拆开细讲：
重点看 GroupChat 怎么决定"该谁说话"，以及对话怎么推进到收敛。

AutoGen 的核心机制：
    1. ConversableAgent：每个角色能收消息、回消息
    2. GroupChat：把多个 Agent 拉进一个会话
    3. speaker_selection_strategy：决定下一句轮到谁
       - auto     : 由 LLM 根据上下文选（这里用关键词模拟）
       - round_robin: 按列表顺序轮流
       - manual   : 人工指定
    4. max_round : 防止无限聊下去

运行方式：
    python demo2_autogen_conversation_driven.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ConversableAgent:
    name: str
    system_message: str
    # reply(收到的消息, 发送者名字) -> 我的回复
    reply: Callable[[str, str], str]


@dataclass
class GroupChat:
    agents: list[ConversableAgent]
    # speaker_selector(所有Agent, 当前轮次, 上一条消息) -> 下一个说话者
    speaker_selector: Callable[[list[ConversableAgent], int, str], ConversableAgent]
    max_round: int = 6
    messages: list[str] = field(default_factory=list)

    def run(self, initiator: ConversableAgent, prompt: str) -> str:
        print(f"[GroupChat] 发起者={initiator.name}，初始问题：{prompt}")
        # initiator 先真正发言一次（用自己的 reply 产生第一句回复）
        first_reply = initiator.reply(prompt, initiator.name)
        self.messages.append(f"{initiator.name}: {first_reply}")
        print(f"  发起 [{initiator.name}] -> {first_reply}")
        last_msg = first_reply

        for turn in range(self.max_round):
            # 谁接话由 speaker_selector 决定
            current_speaker = self.speaker_selector(self.agents, turn, last_msg)
            response = current_speaker.reply(last_msg, current_speaker.name)
            self.messages.append(f"{current_speaker.name}: {response}")
            print(f"  轮次 {turn+1} [{current_speaker.name}] -> {response}")

            # 收敛条件：总结员发言后结束（真实 AutoGen 用 is_termination_msg 判断）
            if "最终结论" in response:
                print(f"[GroupChat] 总结员已收敛，对话结束。")
                return response
            last_msg = response

        print(f"[GroupChat] 达到最大轮次 {self.max_round}，强制结束。")
        return last_msg


# ---------------- 角色实现（每个角色的"回话"逻辑） ----------------

def researcher_reply(msg: str, speaker: str) -> str:
    # 研究员：收到问题就给要点
    return "研究员：要点1=轻量；要点2=可控；要点3=可观测。请评审。"


def critic_reply(msg: str, speaker: str) -> str:
    # 评审员：收到研究员的要点就挑刺
    if "要点" in msg:
        return '评审员：要点2的"可控"需要补充：状态机化才能可控。'
    return "评审员：请研究员先给要点。"


def summarizer_reply(msg: str, speaker: str) -> str:
    # 总结员：评审通过后做总结收敛
    if "补充" in msg or "可控" in msg:
        return "总结员：最终结论=轻量+状态机可控+可观测，推荐 LangGraph。"
    return "总结员：还在等评审，先不总结。"


# ---------------- speaker 选择策略 ----------------

def auto_speaker(agents: list[ConversableAgent], turn: int, last_msg: str) -> ConversableAgent:
    """模拟 AutoGen 的 auto 策略：用关键词判断该谁接话。

    真实 AutoGen 会把对话历史喂给 LLM，让 LLM 选下一个说话者。
    这里用关键词规则模拟，方便你理解"为什么需要这个机制"。
    """
    by_name = {a.name: a for a in agents}
    # 研究员给完要点会带"请评审" → 轮到评审员
    if "请评审" in last_msg:
        return by_name["critic"]
    # 评审员给完修改意见会带"补充" → 轮到总结员收敛
    if "补充" in last_msg:
        return by_name["summarizer"]
    # 评审员还在等要点 → 研究员补要点
    if "请研究员先给要点" in last_msg:
        return by_name["researcher"]
    # 默认交给总结员，避免卡住
    return by_name["summarizer"]


def run_demo() -> None:
    print("=" * 70)
    print("AutoGen 对话驱动：研究员 → 评审员 → 总结员，靠说话推进")
    print("=" * 70)

    agents = [
        ConversableAgent("researcher", "你是研究员", researcher_reply),
        ConversableAgent("critic", "你是评审员", critic_reply),
        ConversableAgent("summarizer", "你是总结员", summarizer_reply),
    ]

    chat = GroupChat(agents, speaker_selector=auto_speaker, max_round=6)
    final = chat.run(agents[0], "调研多智能体框架的选型")

    print(f"\n最终产出：{final}")
    print("\n本 demo 重点：")
    print("  1. 多个 Agent 在一个会话里轮流说话")
    print("  2. 谁接话由 speaker_selector 决定（这里模拟 auto 策略）")
    print("  3. 靠'总结员收敛'判断结束，对应真实 AutoGen 的 termination 条件")


if __name__ == "__main__":
    run_demo()
