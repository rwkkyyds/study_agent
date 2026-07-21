"""
demo4_celery_fastapi.py — FastAPI + Celery 集成：API 触发后台任务

学习目标：
1. FastAPI 中发送 Celery 任务（.delay()）
2. 轮询任务状态（AsyncResult）
3. 获取任务结果

运行：
  终端1: celery -A demo4_celery_fastapi.celery_app worker --pool=solo -l info
  终端2: python demo4_celery_fastapi.py
  终端3: curl http://127.0.0.1:8000/docs
"""

import time
import logging
import atexit
from celery import Celery
from fastapi import FastAPI
import uvicorn

atexit.register(lambda: None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Celery 配置
# ──────────────────────────────────────────────
celery_app = Celery(
    "demo4",
    broker="redis://localhost:6379/3",
    backend="redis://localhost:6379/3",
)


@celery_app.task(name="generate_report", bind=True)
def generate_report(self, user_id: int, report_type: str):
    """
    模拟生成报告（耗时操作）
    通过 self.update_state 报告进度
    """
    logger.info(f"  为用户 {user_id} 生成 {report_type} 报告...")

    steps = ["查询数据", "生成图表", "排版格式", "导出PDF"]
    for i, step in enumerate(steps):
        time.sleep(1.5)  # 模拟耗时
        # 更新进度
        self.update_state(
            state="PROGRESS",
            meta={"step": step, "progress": (i + 1) / len(steps) * 100}
        )

    logger.info(f"  报告生成完成")
    return {
        "report_url": f"/reports/{user_id}_{report_type}.pdf",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ──────────────────────────────────────────────
# FastAPI 应用
# ──────────────────────────────────────────────
app = FastAPI(title="Celery + FastAPI 示例", version="1.0")


@app.post("/reports/{user_id}")
async def create_report(user_id: int, report_type: str = "weekly"):
    """
    触发报告生成任务（异步）
    返回 task_id，前端可以用它轮询进度
    """
    task = generate_report.delay(user_id, report_type)
    return {
        "task_id": task.id,
        "status": "任务已提交到队列",
        "check_url": f"/tasks/{task.id}",
    }


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    查询任务状态和进度
    前端 AJAX 轮询此接口获取实时进度
    """
    task = celery_app.AsyncResult(task_id)

    response = {"task_id": task_id, "status": task.state}

    if task.state == "PROGRESS":
        # Worker 通过 update_state 设置的进度信息
        response.update(task.info or {})
    elif task.state == "SUCCESS":
        response["result"] = task.result
    elif task.state == "FAILURE":
        response["error"] = str(task.info)

    return response


@app.get("/")
async def root():
    return {
        "service": "Celery + FastAPI 异步任务 Demo",
        "endpoints": {
            "POST /reports/{user_id}": "触发报告生成",
            "GET /tasks/{task_id}": "查询任务进度",
        },
    }


# ──────────────────────────────────────────────
# 架构图
# ──────────────────────────────────────────────
def print_architecture():
    print("""
┌─────────────────────────────────────────────────────────┐
│                     Celery + FastAPI 架构                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  FastAPI (Web)          Redis (Broker)    Celery Worker │
│  ┌─────────┐           ┌─────────┐       ┌──────────┐  │
│  │ POST    │──.delay()→│ Queue   │──→   │ @task    │  │
│  │ /report │           │         │       │ generate │  │
│  └─────────┘           └─────────┘       └──────────┘  │
│       ↑                                     ↓          │
│       │  ┌─────────┐               ┌──────────┐       │
│       └──│ GET     │←──.get()──────│ Result   │       │
│          │ /task/1 │               │ Backend  │       │
│          └─────────┘               └──────────┘       │
│                                                         │
│  API 收到请求 → .delay() 发送到 Redis → Worker 执行     │
│  前端轮询 GET /tasks/{id} → 实时获取进度                │
└─────────────────────────────────────────────────────────┘
""")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print_architecture()
    print("启动 FastAPI 服务...")
    print("记得先启动 Worker：celery -A demo4_celery_fastapi.celery_app worker --pool=solo -l info")
    uvicorn.run(app, host="127.0.0.1", port=8000)
