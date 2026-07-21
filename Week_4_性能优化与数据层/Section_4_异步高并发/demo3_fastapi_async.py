"""
demo3_fastapi_async.py — FastAPI 异步端点：async def 的正确用法与陷阱

学习目标：
1. FastAPI 的 async def vs def 端点区别
2. run_in_executor() — 把 CPU 密集任务丢到线程池
3. BackgroundTasks — 不阻塞响应的后台任务
4. 阻塞陷阱的真实演示（让服务卡死）

运行：python demo3_fastapi_async.py
测试：浏览器访问 http://127.0.0.1:8000/docs
      或 curl http://127.0.0.1:8000/
"""

import asyncio
import time
import logging
from fastapi import FastAPI, BackgroundTasks
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="异步高并发 Demo", version="1.0")

# 全局计数器 — 追踪并发请求数
active_requests = 0


# ──────────────────────────────────────────────
# 路由 1：async def 端点 — IO 不阻塞
# ──────────────────────────────────────────────
@app.get("/")
async def root():
    """
    普通 async def 端点 — 模拟 IO 操作（如查数据库、调外部 API）
    因为用了 await asyncio.sleep（非阻塞），多个请求可以同时处理
    """
    global active_requests
    active_requests += 1
    req_id = active_requests
    logger.info(f"  [请求{req_id}] 进入")

    # await asyncio.sleep 是异步的 — 让出事件循环给其他请求
    await asyncio.sleep(1.0)

    active_requests -= 1
    logger.info(f"  [请求{req_id}] 退出（当前活跃：{active_requests}）")
    return {"message": f"请求 {req_id} 处理完成（非阻塞，其他请求不受影响）"}


# ──────────────────────────────────────────────
# 路由 2：同步阻塞端点 — 灾难演示！
# ──────────────────────────────────────────────
@app.get("/block")
def block():
    """
    ⚠️ 同步端点内调 time.sleep() — 阻塞整个事件循环！
    访问这个端点时，其他所有请求（包括 / 路由）全部排队等待
    """
    global active_requests
    active_requests += 1
    req_id = active_requests
    logger.info(f"  [阻塞请求{req_id}] 进入 — 整个服务将被卡住 3 秒！")

    # time.sleep 是同步阻塞的 — 事件循环无法处理其他请求
    time.sleep(3.0)

    active_requests -= 1
    logger.info(f"  [阻塞请求{req_id}] 退出")
    return {"message": f"阻塞请求 {req_id} 完成（期间服务无法处理其他请求！）"}


# ──────────────────────────────────────────────
# 路由 3：run_in_executor — CPU 密集任务
# ──────────────────────────────────────────────
@app.get("/cpu")
async def cpu_task():
    """
    【run_in_executor】把 CPU 密集函数丢到线程池执行，不阻塞事件循环
    适用：图像处理、大 JSON 解析、Pandas 计算等
    """
    def heavy_computation():
        """模拟 CPU 密集操作 — 阻塞型函数"""
        total = 0
        for i in range(10_000_000):
            total += i  # 纯 CPU 计算，asyncio 无法切换
        return total

    # 在线程池中执行，await 等结果 — 事件循环继续处理其他请求
    loop = asyncio.get_running_loop()  #get_running_loop() 获取当前事件循环 
    result = await loop.run_in_executor(None, heavy_computation) 
    #run_in_executor(None, func) 将函数提交到默认线程池执行，返回一个 Future 对象，await 等待结果
    #当 executor=None，事件循环内部会懒加载一个全局 ThreadPoolExecutor
    return {"result": result, "note": "CPU 密集任务在线程池执行，未阻塞其他请求"}


# ──────────────────────────────────────────────
# 路由 4：BackgroundTasks — 不阻塞响应
# ──────────────────────────────────────────────
@app.post("/send-email")
async def send_email(background_tasks: BackgroundTasks, to: str = "user@example.com"):
    """
    【BackgroundTasks】响应返回后继续执行的后台任务
    适用：发邮件、写日志、清理缓存等"不需要等结果"的操作
    """

    async def send_email_async(email: str):
        """模拟耗时操作（如发邮件）"""
        await asyncio.sleep(2.0)
        logger.info(f"  ✅ 邮件已发送至 {email}")

    background_tasks.add_task(send_email_async, to)
    return {"message": f"请求已接受，邮件将在后台发送至 {to}", "note": "响应不等待邮件发送完成"}


# ──────────────────────────────────────────────
# 路由 5：def 端点 vs async def 端点
# ──────────────────────────────────────────────
@app.get("/compare")
async def compare():
    """
    FastAPI 处理模型：
    - async def → 由事件循环直接调用（单线程异步）
    - def → 在线程池中执行（不会阻塞事件循环，但有线程开销）
    """
    return {
        "async_def": "事件循环直接调度 → IO 密集场景最优",
        "def":      "在线程池执行 → 适合调用同步库（如 pandas、psycopg2）",
        "建议":     "IO 密集用 async def / CPU 密集用 def 或 run_in_executor",
    }


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════╗
║  FastAPI 异步端点演示                         ║
╠══════════════════════════════════════════════╣
║ 测试方法（开多个终端同时 curl）：              ║
║                                              ║
║  终端1: curl http://127.0.0.1:8000/          ║
║  终端2: curl http://127.0.0.1:8000/          ║
║  → 两个请求 1s 内都返回（非阻塞）              ║
║                                              ║
║  终端1: curl http://127.0.0.1:8000/block     ║
║  终端2: curl http://127.0.0.1:8000/          ║
║  → 终端2 等 3s 才返回（被 block 卡住）         ║
╚══════════════════════════════════════════════╝
""")
    uvicorn.run(app, host="127.0.0.1", port=8000)














