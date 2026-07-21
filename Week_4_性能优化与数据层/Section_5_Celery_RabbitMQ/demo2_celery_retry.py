"""
demo2_celery_retry.py — Celery 自动重试与指数退避

学习目标：
1. autoretry_for — 自动捕获指定异常并重试
2. retry_backoff — 指数退避（1s → 2s → 4s → 8s ...）2^n次方 n是重试次数
3. max_retries — 最大重试次数
4. retry_kwargs — 自定义重试参数

运行：python demo2_celery_retry.py
"""

import random
import logging
import atexit
from celery import Celery

atexit.register(lambda: None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

celery_app = Celery(
    "demo2",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/1",
)


# ──────────────────────────────────────────────
# 场景 1：自动重试 — 调用不稳定的外部 API
# ──────────────────────────────────────────────
@celery_app.task(
    name="call_unstable_api",
    bind=True,
    autoretry_for=(Exception,),  # 【autoretry_for】捕获哪些异常时自动重试
    retry_backoff=True,          # 【retry_backoff】指数退避：第1次等1s，第2次等2s...
    retry_backoff_max=10,        # 退避最大等待 10s
    max_retries=3,               # 【max_retries】最多重试 3 次
)
def call_unstable_api(self, api_name: str):
    """
    模拟不稳定的第三方 API 调用
    50% 概率失败，失败后自动重试
    """
    logger.info(f"  [{api_name}] 第 {self.request.retries + 1} 次尝试...")

    if random.random() > 0.5:
        logger.info(f"  [{api_name}] [OK] 成功！")
        return f"{api_name} 调用成功（第 {self.request.retries + 1} 次尝试）"
    else:
        logger.warning(f"  [{api_name}] [FAIL] 失败，将自动重试")
        raise Exception(f"{api_name} 暂时不可用")


# ──────────────────────────────────────────────
# 场景 2：手动重试 — 根据条件决定是否重试
# ──────────────────────────────────────────────
@celery_app.task(name="smart_retry", bind=True, max_retries=3)
def smart_retry(self, order_id: int):
    """
    智能重试：根据业务条件决定是否重试
    【self.retry()】手动触发重试，可传自定义参数
    """
    logger.info(f"  处理订单 {order_id}，第 {self.request.retries + 1} 次尝试")

    # 模拟：订单状态为 "pending" → 等一会重试
    #       订单状态为 "cancelled" → 不重试，直接失败
    status = random.choice(["pending", "pending", "pending", "cancelled"])

    if status == "cancelled":
        logger.warning(f"  订单 {order_id} 已取消，不重试")
        return f"订单 {order_id} 已取消"

    if self.request.retries < 3:
        logger.info(f"  订单 {order_id} 仍在处理中，{2 ** self.request.retries}s 后重试")
        # 【self.retry()】手动重试
        # countdown：延迟 N 秒后重试
        raise self.retry(countdown=2 ** self.request.retries) 
    

    logger.error(f"  订单 {order_id} 重试耗尽！")
    return f"订单 {order_id} 处理失败（已达最大重试次数）"


# ──────────────────────────────────────────────
# 场景 3：指数退避可视化
# ──────────────────────────────────────────────
def show_backoff_strategy():
    """展示不同 retry_backoff 策略的等待时间"""
    print("\n── 指数退避策略 ──")
    print("  重试次数  |  backoff=1  |  backoff=2  |  backoff=3")
    print("  ----------|-------------|-------------|------------")
    for attempt in range(1, 6):
        # 公式：countdown = backoff * 2^(retries)，retries 从 0 开始
        # backoff 只是一个系数，底数永远是 2
        b1 = min(2 ** (attempt - 1), 60)       # backoff=1: 1 * 2^0=1s, 1*2^1=2s, 1*2^2=4s...
        b2 = min(2 * 2 ** (attempt - 1), 60)   # backoff=2: 2 * 2^0=2s, 2*2^1=4s, 2*2^2=8s...
        b3 = min(3 * 2 ** (attempt - 1), 60)   # backoff=3: 3 * 2^0=3s, 3*2^1=6s, 3*2^2=12s...
        print(f"  第{attempt}次     |  {b1}s          |  {b2}s          |  {b3}s")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Celery 重试与指数退避演示")
    print("=" * 60)

    # 检查 Worker 是否在运行
    try:
        from celery.result import AsyncResult
        test = celery_app.send_task("call_unstable_api", args=["连通测试"], expires=3) #.send_task() 发送任务到队列
        test.get(timeout=3)
    except Exception:
        print("\n[!] 请先在另一个终端启动 Worker：")
        print("  celery -A demo2_celery_retry.celery_app worker --pool=solo -l info")
        exit(1)

    show_backoff_strategy()

    print("\n── 自动重试演示（50% 失败率）──")
    for api in ["支付网关", "短信服务", "邮件服务"]:
        try:
            result = call_unstable_api.delay(api).get(timeout=30)
            print(f"  → {result}")
        except Exception:
            print(f"  → {api} 调用失败（重试耗尽）")

    print("\n── 智能重试演示 ──")
    for oid in [101, 102, 103]:
        try:
            result = smart_retry.delay(oid).get(timeout=30)
            print(f"  → {result}")
        except Exception:
            print(f"  → 订单 {oid} 处理异常")

    print("\n[OK] demo2 完成！")
