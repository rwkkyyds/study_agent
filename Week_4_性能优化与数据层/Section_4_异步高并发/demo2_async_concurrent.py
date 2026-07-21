"""
demo2_async_concurrent.py — asyncio 并发编排：gather / create_task / 超时

学习目标：
1. asyncio.gather() — 同时发起，等全部完成
2. asyncio.create_task() — 后台运行，不阻塞当前协程
3. asyncio.wait_for() — 带超时的并发调用
4. 串行 vs 并发真实计时对比（加速比）

运行：python demo2_async_concurrent.py
"""

import asyncio
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 模拟 IO 密集型任务
# ──────────────────────────────────────────────
async def io_task(name: str, delay: float) -> str:
    logger.info(f"  [{name}] 开始（需 {delay}s）")
    await asyncio.sleep(delay)
    logger.info(f"  [{name}] 完成")
    return f"{name} 结果"


def sync_task(name: str, delay: float) -> str:
    """同步版 — 用于演示阻塞灾难"""
    logger.info(f"  [{name}] 开始（需 {delay}s）")
    time.sleep(delay)  # ← 阻塞！
    logger.info(f"  [{name}] 完成")
    return f"{name} 结果"


# ──────────────────────────────────────────────
# Step 1：串行 vs 并发 — 加速比
# ──────────────────────────────────────────────
async def demo_serial_vs_concurrent():
    delays = [0.5, 0.3, 0.8, 0.4, 0.6]  # 总串行耗时 2.6s

    # ── 串行 ──
    print("\n── 串行（逐个 await）──")
    t0 = time.perf_counter()
    for i, d in enumerate(delays):
        await io_task(f"Task-{i}", d)
    serial = time.perf_counter() - t0
    print(f"  串行耗时：{serial:.2f}s（{sum(delays):.1f}s 总和）")

    # ── 并发 ──
    print("\n── 并发（gather 同时发起）──")
    t0 = time.perf_counter()
    await asyncio.gather(*(io_task(f"Task-{i}", d) for i, d in enumerate(delays)))
    concurrent = time.perf_counter() - t0
    print(f"  并发耗时：{concurrent:.2f}s（≈ 最慢任务 {max(delays)}s）")
    print(f"  加速比：{serial / concurrent:.1f}x")


# ──────────────────────────────────────────────
# Step 2：gather vs create_task
# ──────────────────────────────────────────────
async def demo_gather_vs_create_task():
    print("\n── gather：阻塞等待全部完成 ──")
    results = await asyncio.gather(io_task("A", 0.3), io_task("B", 0.2))
    print(f"  gather 返回：{results}")

    print("\n── create_task：后台运行，主协程不阻塞 ──")
    t1 = asyncio.create_task(io_task("C", 1.0))
    t2 = asyncio.create_task(io_task("D", 0.5))
    logger.info("  主协程继续做其他事...")
    await asyncio.sleep(0.1)
    logger.info("  现在收集结果...")
    r1, r2 = await t1, await t2
    print(f"  create_task 结果：{r1}, {r2}")


# ──────────────────────────────────────────────
# Step 3：超时控制 — wait_for
# ──────────────────────────────────────────────
async def demo_timeout():
    """生产常见：调外部 API 设超时，防止一个慢服务拖死整个请求"""
    print("\n── wait_for 超时 ──")
    try:
        result = await asyncio.wait_for(io_task("SlowAPI", 2.0), timeout=0.5)
    except asyncio.TimeoutError:
        print("  ⚠️ SlowAPI 超时！返回降级默认值")
        result = "降级默认值"
    print(f"  最终结果：{result}")


# ──────────────────────────────────────────────
# Step 4：阻塞陷阱 — 为什么 async 里不能调同步阻塞函数
# ──────────────────────────────────────────────
async def demo_blocking_pitfall():
    """⚠️ async def 里调用 time.sleep() = 整个事件循环被卡死"""
    print("\n── 阻塞陷阱 ──")
    t0 = time.perf_counter()
    sync_task("BLOCK-1", 0.3)
    sync_task("BLOCK-2", 0.3)
    elapsed = time.perf_counter() - t0
    print(f"  串行阻塞耗时：{elapsed:.2f}s")
    print("  ⚠️ 如果这是 FastAPI async def 端点，整个服务被这一个请求卡住！")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
async def main():
    await demo_serial_vs_concurrent()
    await demo_gather_vs_create_task()
    await demo_timeout()
    await demo_blocking_pitfall()


if __name__ == "__main__":
    asyncio.run(main())
    print("\n✅ demo2 完成！")
