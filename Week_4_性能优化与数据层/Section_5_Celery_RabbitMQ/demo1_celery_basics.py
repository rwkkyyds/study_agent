"""
demo1_celery_basics.py — Celery 异步任务队列基础

学习目标：
1. Celery 架构：Producer → Broker(Redis) → Worker → Result Backend
2. 定义任务（@celery_app.task）、异步调用（.delay()）、获取结果（.get()）
3. 理解 Worker 是独立进程，任务异步执行

运行前先启动 Redis 和 Worker：
  终端1: docker run -d --name redis -p 6379:6379 redis:7-alpine
  终端2: celery -A demo1_celery_basics.celery_app worker --loglevel=info --pool=solo
  终端3: python demo1_celery_basics.py
"""

import time
import logging
import atexit

# 避免 Python 退出时 redis-py 清理报噪音（不影响功能）
atexit.register(lambda: None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Celery App 配置
# ──────────────────────────────────────────────
from celery import Celery

# 【Celery("name")】创建一个 Celery 应用实例
# broker：消息中间件，Redis 负责在 Producer 和 Worker 之间传递任务
# backend：结果存储，任务执行完后结果存在 Redis 里
celery_app = Celery(
    "demo1",
    broker="redis://localhost:6379/0",   # Redis 作为消息队列
    backend="redis://localhost:6379/0",  # Redis 作为结果存储
)


# ──────────────────────────────────────────────
# 定义任务
# ──────────────────────────────────────────────
@celery_app.task(name="add")
def add(x: int, y: int) -> int:
    """最简单的异步任务 — 加法"""
    return x + y


@celery_app.task(name="slow_task", bind=True) #bind=True 让任务可以访问 self（任务实例）
def slow_task(self, name: str, duration: int):
    """
    模拟耗时任务（如发邮件、生成报告、图片处理）
    【bind=True】让任务可以访问 self（任务实例）
    【self.update_state()】更新任务状态，前端可以轮询进度
    """
    logger.info(f"  [{name}] 任务开始，预计 {duration}s")
    for i in range(duration):
        time.sleep(1)
        # 更新进度状态（仅 Worker 执行时有效，直接调用时跳过）
        if self.request.id: #print(self.request.id )    '1e3f8c9b-5d2a-4f3e-9c6b-1a2b3c4d5e6f'
            self.update_state(
                state="PROGRESS",  
                meta={"current": i + 1, "total": duration}
            )
    logger.info(f"  [{name}] 任务完成")
    return f"{name} 完成，耗时 {duration}s"


# ──────────────────────────────────────────────
# 演示：同步 vs 异步
# ──────────────────────────────────────────────
def demo_sync_vs_async():
    """
    同步：调用者等任务执行完才继续
    异步：调用者立即返回，Worker 后台执行
    """
    print("\n── 同步调用（阻塞等待）──")
    t0 = time.time()
    # 直接调用（不走 Celery），等价于普通 Python 函数
    logger.info(f"  [sync-task] 任务开始，预计 2s")
    time.sleep(2)
    result = f"sync-task 完成，耗时 2s"
    print(f"  结果：{result}")
    print(f"  耗时：{time.time() - t0:.1f}s（调用的地方被阻塞了）")

    print("\n── 异步调用（.delay() 立即返回）──")
    t0 = time.time()
    # 【.delay()】把任务发送到队列，立即返回 AsyncResult
    task = slow_task.delay("async-task", 3)
    print(f"  任务 ID：{task.id}")
    print(f"  任务状态：{task.status}")  # PENDING — Worker 还没处理 
    print(f"  .delay() 返回耗时：{time.time() - t0:.2f}s（立即返回！）")

    print("\n  等待 Worker 处理...")
    # 【.get()】阻塞等待任务完成并获取结果
    result = task.get(timeout=10)
    print(f"  任务结果：{result}")
    print(f"  最终状态：{task.status}")  # SUCCESS


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Celery 异步任务队列演示")
    print("=" * 60)
    print("""
架构图：
  Producer(.delay) → Broker(Redis) → Worker(独立进程) → Result Backend(Redis)
      你在这里            ↓                ↓                   ↓
    发送任务消息      消息队列存储      消费并执行任务        存储结果
""")

    try:
        demo_sync_vs_async()
        print("\n[OK] demo1 完成！")
    except Exception as e:
        print(f"\n[!] 请先启动 Redis 和 Celery Worker：")
        print("  docker run -d --name redis -p 6379:6379 redis:7-alpine")
        print("  celery -A demo1_celery_basics.celery_app worker --loglevel=info --pool=solo")
        print(f"\n原始错误：{e}")
