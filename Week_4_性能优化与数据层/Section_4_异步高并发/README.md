# Section 4：异步高并发 — asyncio + FastAPI 异步改造

## 🎯 学习目标

1. 理解 `async/await`、事件循环、协程的本质（**不是线程！**）
2. 掌握 `asyncio.gather()` 并发执行，直观感受串行 vs 并发的差距
3. FastAPI `async def` 端点的正确用法与**阻塞陷阱**
4. 异步数据库访问（async SQLAlchemy），并发查询性能对比

## 📚 学习顺序

| 顺序 | 文件 | 内容 | 核心技能 |
|------|------|------|----------|
| 1 | `demo1_async_basics.py` | async/await、事件循环、协程 vs 函数 | 协程基础 |
| 2 | `demo2_async_concurrent.py` | gather、create_task、串行 vs 并发计时 | 并发编排 |
| 3 | `demo3_fastapi_async.py` | async def 端点、run_in_executor、阻塞陷阱 | 异步 Web |
| 4 | `demo4_async_db.py` | async SQLAlchemy + 并发 DB 查询 | 异步数据层 |

**前置：** 完成 Section_1~3，熟悉 FastAPI、SQLAlchemy 基础。

## 🚀 运行方式

```bash
pip install fastapi uvicorn sqlalchemy[asyncio] aiosqlite httpx

python demo1_async_basics.py
python demo2_async_concurrent.py
python demo3_fastapi_async.py   # 运行后在另一个终端 curl 测试
python demo4_async_db.py
```

## ⚠️ 核心认知（记住这三句话）

- **async ≠ 快**，async 是**不等待**——IO 等待时切走干别的事
- **async def 里千万别调 `time.sleep()`**，会卡死整个事件循环
- CPU 密集任务用 `run_in_executor()` 丢到线程池

## 🔄 推荐复习

- Week_1 Section_1：FastAPI 路由与异步 I/O
- Week_4 Section_2：PostgreSQL 连接池

## 📖 下一节

**Section_5 Celery + RabbitMQ**：异步任务队列、消息丢失与重试
