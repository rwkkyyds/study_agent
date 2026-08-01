"""
demo2: 多智能体系统的异常处理与容错

单个 Agent 可能：超时、报错、输出垃圾、无限循环。
多智能体系统必须保证：一个 Agent 挂了，不能拖垮整个系统。

本 demo 实现四层容错：
    1. 超时保护：单个 Agent 执行有时间上限
    2. 自动重试：失败后指数退避重试（最多3次）
    3. 降级输出：重试耗尽后用兜底结果，不阻塞流程
    4. 熔断保护：连续失败的 Agent 被熔断，后续直接跳过

运行方式：
    python demo2_resilient_multiagent.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


# =====================================================================
# 第一部分：容错工具——超时、重试、降级、熔断
# =====================================================================

class CircuitBreaker:
    """熔断器：连续失败 N 次后熔断，一段时间内直接跳过。

    三态：closed（正常）→ open（熔断，拒绝调用）→ half_open（试探）
    生产级系统常用，这里简化为两态 + 计数。
    """
    def __init__(self, threshold: int = 3, cooldown: float = 5.0) -> None:
        self.threshold = threshold  # 连续失败多少次触发熔断
        self.cooldown = cooldown     # 熔断后冷却多久（秒）
        self.fail_count = 0
        self.opened_at: float | None = None  # 熔断打开时间

    def is_open(self) -> bool:
        """是否处于熔断状态。"""
        if self.opened_at is None:
            return False
        if time.time() - self.opened_at > self.cooldown:
            print("    [熔断器] 冷却结束，进入半开试探")
            self.opened_at = None
            self.fail_count = 0
            return False
        return True

    def record_failure(self) -> None:
        self.fail_count += 1
        if self.fail_count >= self.threshold:
            self.opened_at = time.time()
            print(f"    [熔断器] 连续失败{self.fail_count}次，已熔断")

    def record_success(self) -> None:
        self.fail_count = 0
        self.opened_at = None


def call_with_resilience(
    agent_name: str,
    handler: Callable[[str], str],
    user_input: str,
    max_retries: int = 3,
    timeout: float = 0.5,
    fallback: str = "【降级输出】该环节暂不可用，已用兜底结果",
    breaker: CircuitBreaker | None = None,
) -> str:
    """带容错的 Agent 调用：熔断检查 → 超时 → 重试 → 降级。

    这是多智能体容错的"标准模板"，生产里每个 Agent 调用都该套这层。
    """
    # 第1层：熔断检查——已熔断的直接跳过
    if breaker and breaker.is_open():
        return f"  [{agent_name}] 已熔断，跳过 -> {fallback}"

    last_error: str = ""
    for attempt in range(1, max_retries + 1):
        try:
            # 第2层：超时保护——用线程+join 模拟（这里用 time 简化）
            start = time.time()
            result = handler(user_input)
            elapsed = time.time() - start
            if elapsed > timeout:
                raise TimeoutError(f"执行耗时{elapsed:.2f}s 超过上限{timeout}s")

            # 成功，重置熔断器
            if breaker:
                breaker.record_success()
            return f"  [{agent_name}] 第{attempt}次成功 -> {result}"

        except TimeoutError as e:
            last_error = f"超时:{e}"
            print(f"    [{agent_name}] 第{attempt}次失败：{e}")
        except Exception as e:
            last_error = f"异常:{e}"
            print(f"    [{agent_name}] 第{attempt}次失败：{e}")

        # 第3层：指数退避——重试前等待（base * 2^attempt）
        if attempt < max_retries:
            backoff = 0.1 * (2 ** (attempt - 1))
            print(f"    [{agent_name}] 等待{backoff}s 后重试...")
            time.sleep(backoff)

    # 第4层：降级输出——重试耗尽，返回兜底
    if breaker:
        breaker.record_failure()
    print(f"    [{agent_name}] 重试耗尽，降级处理")
    return f"  [{agent_name}] 降级 -> {fallback}（原因：{last_error}）"


# =====================================================================
# 第二部分：模拟一个会出故障的多智能体流水线
# =====================================================================

def fast_agent(msg: str) -> str:
    """正常 Agent，秒回。"""
    return f"已处理：{msg}"

def slow_agent(msg: str) -> str:
    """慢 Agent，故意超过超时上限。"""
    time.sleep(0.8)  # 超过 timeout=0.5
    return f"慢处理完：{msg}"

def flaky_agent(msg: str) -> str:
    """不稳定 Agent，前两次抛异常，第三次才成功。"""
    flaky_agent.calls += 1
    if flaky_agent.calls < 3:
        raise RuntimeError(f"内部错误（第{flaky_agent.calls}次）")
    return f"终于成功：{msg}"
flaky_agent.calls = 0  # 静态计数器

def always_fail_agent(msg: str) -> str:
    """永远失败的 Agent，用于演示熔断和降级。"""
    raise RuntimeError("永久故障")


def run_demo() -> None:
    print("=" * 70)
    print("场景1：正常 Agent，秒回")
    print("=" * 70)
    result = call_with_resilience("fast", fast_agent, "工单A")
    print(result)

    print("\n" + "=" * 70)
    print("场景2：慢 Agent，触发超时 → 重试 → 最终降级")
    print("=" * 70)
    result = call_with_resilience("slow", slow_agent, "工单B", timeout=0.3)
    print(result)

    print("\n" + "=" * 70)
    print("场景3：不稳定 Agent，前两次失败，第三次成功")
    print("=" * 70)
    flaky_agent.calls = 0
    result = call_with_resilience("flaky", flaky_agent, "工单C", max_retries=3)
    print(result)

    print("\n" + "=" * 70)
    print("场景4：永久故障 Agent，触发熔断（连续3次失败）")
    print("=" * 70)
    breaker = CircuitBreaker(threshold=3, cooldown=5.0)
    for i in range(4):
        print(f"  --- 第{i+1}次调用 ---")
        result = call_with_resilience(
            "broken", always_fail_agent, f"工单D{i}",
            breaker=breaker,
        )
        print(result)
        if breaker.is_open():
            print("  （熔断器已打开，后续调用会直接跳过）")

    print("\n" + "=" * 70)
    print("容错总结：")
    print("  1. 超时：防止单个 Agent 卡死整个流程")
    print("  2. 重试：临时故障自动恢复，指数退避避免雪崩")
    print("  3. 降级：重试耗尽用兜底结果，不阻塞下游")
    print("  4. 熔断：永久故障的 Agent 被隔离，不再浪费资源")


if __name__ == "__main__":
    run_demo()
