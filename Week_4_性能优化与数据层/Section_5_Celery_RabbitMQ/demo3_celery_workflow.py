"""
demo3_celery_workflow.py — Celery 任务编排：Chain / Group / Chord

学习目标：
1. chain：串行任务链（A → B → C，前一个的输出是后一个的输入）
2. group：并行任务组（同时执行多个任务）
3. chord：group + 回调（并行结束后执行汇总任务）

运行：python demo3_celery_workflow.py
"""

import logging
import atexit
from celery import Celery, chain, group, chord

atexit.register(lambda: None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

celery_app = Celery(
    "demo3",
    broker="redis://localhost:6379/2",
    backend="redis://localhost:6379/2",
)


# ──────────────────────────────────────────────
# 定义工作流中的任务
# ──────────────────────────────────────────────
@celery_app.task(name="fetch_data")
def fetch_data(source: str) -> dict:
    """模拟从数据源获取数据"""
    logger.info(f"  从 {source} 获取数据")
    return {"source": source, "count": len(source) * 10, "raw": source.upper()}


@celery_app.task(name="process_data")
def process_data(data: dict) -> dict:
    """
    处理上一步传过来的数据
    【关键】chain 中前一个任务的返回值会自动作为下一个任务的第一个参数
    """
    logger.info(f"  处理数据：{data['source']}")
    return {
        **data, #print(type(**data))     # <class 'dict'>  # 解包字典
        "processed": True,
        "summary": f"处理了 {data['count']} 条记录",
    }


@celery_app.task(name="save_result")
def save_result(data: dict) -> str:
    """保存最终结果"""
    logger.info(f"  保存结果：{data['summary']}")
    return f"结果已保存：{data['summary']}"


@celery_app.task(name="analyze")
def analyze(topic: str) -> str:
    """并行分析任务"""
    logger.info(f"  分析主题：{topic}")
    return f"{topic} 分析完成"


# ──────────────────────────────────────────────
# Step 1：chain — 串行任务链
# ──────────────────────────────────────────────
def demo_chain():
    """
    【chain】A → B → C
    前一个返回值 → 下一个的第一个参数
    类比：流水线
    """
    print("\n── Chain 串行链：fetch → process → save ──")

    # chain(task1, task2, task3)(args) — 语法糖
    workflow = chain(
        fetch_data.s("user_events"),   # 【.s()】创建任务签名（signature），不立即执行
        process_data.s(),              # 接收上一步返回值作为第一个参数
        save_result.s(),               # 同上
    )
    result = workflow().get(timeout=10)
    print(f"  Chain 结果：{result}")


# ──────────────────────────────────────────────
# Step 2：group — 并行执行
# ──────────────────────────────────────────────
def demo_group():
    """
    【group】同时执行 N 个任务，互不依赖
    类比：同时向 3 个数据源发起请求
    """
    print("\n── Group 并行组：同时分析 3 个维度 ──")

    workflow = group(
        analyze.s("用户行为"),
        analyze.s("销售数据"),
        analyze.s("库存状态"),
    )
    results = workflow().get(timeout=10)
    print(f"  Group 结果：{results}")


# ──────────────────────────────────────────────
# Step 3：chord — 并行 + 汇总
# ──────────────────────────────────────────────
@celery_app.task(name="summarize")
def summarize(results: list) -> str:
    """
    汇总 group 的并行结果
    chord 中 group 的所有返回值组成 list，传给回调任务
    """
    logger.info(f"  汇总 {len(results)} 份分析结果")
    parts = ", ".join(results)
    return f"汇总报告：{parts}"


def demo_chord():
    """
    【chord】group + callback
    先用 group 并行执行，全部完成后执行回调汇总
    """
    print("\n── Chord 并行+汇总：3 维度分析 → 汇总报告 ──")

    workflow = chord(
        group(
            analyze.s("A"),
            analyze.s("B"),
            analyze.s("C"),
        ),
        summarize.s(),
    )
    result = workflow().get(timeout=10)
    print(f"  Chord 结果：{result}")


# ──────────────────────────────────────────────
# Step 4：组合演示 — Chain of Groups
# ──────────────────────────────────────────────
@celery_app.task(name="notify")
def notify(report: str) -> str:
    """通知用户"""
    logger.info(f"  发送通知：{report[:50]}...")
    return f"已通知：{report[:30]}..."


def demo_chain_of_groups():
    """
    复杂编排：先进 chain（fetch→process→save），再并行分析，最后通知
    """
    print("\n── 复合编排 ──")

    result = chain(
        chord(
            group(analyze.s("用户"), analyze.s("订单"), analyze.s("商品")),
            summarize.s(),
        ),
        notify.s(),
    )().get(timeout=10)
    print(f"  结果：{result}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Celery 任务编排：Chain / Group / Chord")
    print("=" * 60)

    # 检查 Worker 是否在运行
    try:
        test = celery_app.send_task("analyze", args=["连通测试"], expires=3)
        test.get(timeout=3)
    except Exception:
        print("\n⚠️ 请先在另一个终端启动 Worker：")
        print("  celery -A demo3_celery_workflow.celery_app worker --pool=solo -l info")
        exit(1)

    try:
        demo_chain()
        demo_group()
        demo_chord()
        demo_chain_of_groups()
        print("\n[OK] demo3 完成！")
    except Exception as e:
        print(f"\n[!] 请启动 Worker：celery -A demo3_celery_workflow.celery_app worker --pool=solo -l info")
        print(f"原始错误：{e}")
