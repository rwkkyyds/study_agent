"""
demo1_async_basics.py — async/await 协程基础

学习目标：
1. 理解协程（coroutine）vs 普通函数的本质区别
2. 掌握 async def / await / asyncio.run() 的用法
3. 理解事件循环如何调度协程（单线程内"协作式"切换，不是多线程！）

运行：python demo1_async_basics.py
"""

import asyncio
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Step 1：普通函数 vs 协程 — 调用 ≠ 执行
# ──────────────────────────────────────────────
def normal_func():
    return "普通函数：调用即执行"


async def coro_func():
    """【async def】定义一个协程。调用它不执行，只返回 coroutine 对象"""
    return "协程：调用只返回 coroutine 对象，必须 await 或 asyncio.run() 才执行"


def demo_vs():
    print("\n── 普通函数 vs 协程 ──")
    print(f"  normal_func() → {normal_func()}")
    obj = coro_func()
    print(f"  coro_func()   → {obj}")   # <coroutine object ...>
    print(f"  类型           → {type(obj)}")
    print("  ⚠️ 协程不是自动执行的，必须交给事件循环调度！")


# ──────────────────────────────────────────────
# Step 2：asyncio.sleep vs time.sleep — 非阻塞 vs 阻塞
# ──────────────────────────────────────────────
async def async_sleep(name: str, delay: float):
    """
    【asyncio.sleep()】异步等待 — 让出控制权，事件循环去执行其他协程
    这是 asyncio 的核心：在 IO 等待时切走
    """
    logger.info(f"  [{name}] 开始（{delay}s）")
    await asyncio.sleep(delay)   # 非阻塞 — 此时可以切走执行其他协程
    logger.info(f"  [{name}] 完成")
    return f"{name} 结果"


async def demo_async_sleep():
    """演示：并发 3 个 async_sleep，总耗时 ≈ 最慢的那个"""
    print("\n── asyncio.sleep 并发 — 总耗时≈最慢任务 ──")
    t0 = time.perf_counter() # 记录开始时间，为什么不用 time.time()？因为 perf_counter() 更精确，适合计时
    results = await asyncio.gather(
        async_sleep("Task-A", 1.0),
        async_sleep("Task-B", 0.5),
        async_sleep("Task-C", 0.3),
    )
    elapsed = time.perf_counter() - t0
    print(f"  结果：{results}")
    print(f"  耗时：{elapsed:.2f}s（3个任务同时发起，等最慢的 1s）")


# ──────────────────────────────────────────────
# Step 3：事件循环 — 单线程的任务调度器
# ──────────────────────────────────────────────
async def demo_event_loop():
    """
    事件循环 = 一个 while True 循环，不断检查哪些协程可以推进。
    类比：一个人（单线程）同时煮饭、洗衣服、烧水——
    不是同时做，而是"饭在煮时去洗衣服，衣服在洗时去烧水"
    """
    print("""
── 事件循环工作模型 ──
  单线程内：
    协程A 执行中 → await IO → 让出控制权
                                ↓
    事件循环调度 → 协程B 执行中 → await IO → 让出控制权
                                                ↓
    事件循环调度 → 协程A IO完成 → 继续协程A ...
""")


# ──────────────────────────────────────────────
# Step 4：协程 vs 线程 — 本质区别
# ──────────────────────────────────────────────
def demo_coro_vs_thread():
    print("""── 协程 vs 线程 ──
  切换者 ：协程=用户态（await 主动让出）/ 线程=操作系统抢占
  切换成本：协程~100ns / 线程~1-10μs
  内存   ：协程~KB / 线程~8MB
  并发   ：协程=协作式（单线程）/ 线程=抢占式（多核并行）
  10000个：协程=几MB / 线程=80GB
  适用   ：协程=IO密集型 / 线程=CPU密集型
""")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
async def main():
    demo_vs()
    await demo_async_sleep()
    await demo_event_loop()
    demo_coro_vs_thread()


if __name__ == "__main__":
    asyncio.run(main()) #开启一个事件循环，调用上层的协程知道协程完成执行
    print("\n✅ demo1 完成！")
