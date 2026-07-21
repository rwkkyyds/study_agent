# Section 5：Celery 异步任务队列 + RabbitMQ 消息队列基础

## 🎯 学习目标

1. 理解 Celery 架构：**Producer → Broker → Worker → Result Backend**
2. 掌握任务定义、异步调用、结果获取
3. 掌握自动重试、指数退避、死信队列
4. **用 pika 原生操作 RabbitMQ**：Producer / Consumer / Exchange / Queue / Binding
5. 掌握三种 Exchange 类型：direct / topic / fanout
6. 理解消息持久化（delivery_mode=2）和手动 ACK 机制
7. FastAPI + Celery 集成：API 触发后台任务

## 📚 学习顺序

| 顺序 | 文件 | 内容 | 核心技能 |
|------|------|------|----------|
| 1 | `demo1_celery_basics.py` | Celery App、任务定义、异步调用、结果获取 | Celery 基础 |
| 2 | `demo2_celery_retry.py` | 自动重试、指数退避、max_retries | 容错机制 |
| 3 | `demo3_celery_workflow.py` | Chain / Group / Chord 编排 | 任务编排 |
| 4 | `demo4_celery_fastapi.py` | FastAPI + Celery 集成、后台任务 | Web 集成 |
| 🆕 5 | `demo5_rabbitmq_producer_consumer.py` | pika 原生 Producer/Consumer、持久化、手动 ACK | RabbitMQ 基础 |
| 🆕 6 | `demo6_rabbitmq_exchange_types.py` | Direct / Topic / Fanout Exchange 实战 | RabbitMQ 路由 |

## 🚀 运行方式

### 准备工作（只需一次）

```bash
pip install celery redis pika

# 启动 Redis（Celery demo1-4 需要）
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 启动 RabbitMQ（demo5-6 需要）
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
# 首次需等约 10s RabbitMQ 完全就绪
# 管理界面：http://localhost:15672  账号 guest / 密码 guest
```

### 需要 3 个终端

| 终端 | 作用 | 说明 |
|------|------|------|
| 终端1 | Redis / RabbitMQ | Docker 容器，只需启动一次 |
| 终端2 | Celery Worker | demo1-4 需要（每个 demo 独立的 Worker）|
| 终端3 | 运行 demo | python 执行 |

所有命令默认在 `Week_4_性能优化与数据层/Section_5_Celery_RabbitMQ/` 目录下执行。

### demo1 — Celery 基础

```bash
# 终端2：启动 Worker
celery -A demo1_celery_basics.celery_app worker --pool=solo -l info

# 终端3：运行
python demo1_celery_basics.py

# 终端2 Ctrl+C 停止 Worker，再启动下一个
```

### demo2 — 自动重试 + 指数退避

```bash
# 终端2：切换 Worker
celery -A demo2_celery_retry.celery_app worker --pool=solo -l info

# 终端3：运行
python demo2_celery_retry.py
```

### demo3 — Chain / Group / Chord 编排

```bash
# 终端2：切换 Worker
celery -A demo3_celery_workflow.celery_app worker --pool=solo -l info

# 终端3：运行
python demo3_celery_workflow.py
```

### demo4 — FastAPI + Celery 集成

```bash
# 终端2：启动 Worker
celery -A demo4_celery_fastapi.celery_app worker --pool=solo -l info

# 终端3：启动 FastAPI 服务
python demo4_celery_fastapi.py

# 终端4（可选）：curl 测试
curl -X POST "http://127.0.0.1:8000/reports/42?report_type=monthly"
curl http://127.0.0.1:8000/tasks/<返回的task_id>
```

### demo5 — RabbitMQ Producer / Consumer（pika 原生）

```bash
# 终端2：直接运行（不需要启动 Worker，pika 直接操作 RabbitMQ）
python demo5_rabbitmq_producer_consumer.py
# 包含4个演示：Producer发送 → Consumer拉取 → 持久化验证 → Push模式+手动ACK
```

### demo6 — RabbitMQ Exchange 类型实战

```bash
# 终端2：直接运行
python demo6_rabbitmq_exchange_types.py
# 包含3个演示：Direct(精确匹配) → Topic(通配符) → Fanout(广播)
# 运行时可打开 http://localhost:15672 观察 Exchange 和 Queue 的实时变化
```

> 每个 demo 的 `.celery_app` 用不同 Redis DB（/0 /1 /2 /3），互不干扰。也可同时开多个 Worker——分别在不同终端跑即可。

## ⚠️ Windows 注意事项

| 问题 | 说明 |
|------|------|
| 必须 `--pool=solo` | Windows 不支持 fork，默认 prefork 直接报错 |
| 先开 Worker 再跑 demo | 没 Worker 时 demo 会提示你启动 |
| Python 退出噪音 | `ImportError: sys.meta_path is None` 不影响功能，已加 atexit 处理 |
| 一个 Worker 只对应一个 demo | 每个 demo 有独立的 celery_app，需分别启动 Worker |

## 🔄 推荐复习

- Week_4 Section_1：Redis 工程化（Pub/Sub 部分）
- Week_4 Section_4：asyncio 高并发（异步思维）

## 📖 下一节

**Section_6 批处理优化**：Embedding/Reranker 批处理优化吞吐
