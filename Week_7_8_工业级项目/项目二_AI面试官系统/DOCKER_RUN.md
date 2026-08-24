# Docker 本地启动与使用指南

## 1. 启动

在项目根目录执行：

```powershell
cd "C:\Users\admin\Desktop\agent_study\Week_7_8_工业级项目\项目二_AI面试官系统"
docker compose up --build -d
```

启动后访问：

- 面试页面：http://localhost:8100/web/
- API 文档：http://localhost:8100/docs
- 健康检查：http://localhost:8100/health
- 就绪检查：http://localhost:8100/health/ready

## 2. 查看状态和日志

```powershell
docker compose ps
docker compose logs -f app worker
```

只看最近日志：

```powershell
docker compose logs --tail=100 app worker
```

## 3. 通义千问配置

默认 `LLM_PROVIDER=mock`，系统使用本地确定性规则链路，适合先跑通流程。

如需启用通义千问增强，请在当前 PowerShell 会话或 `.env` 中设置：

```powershell
$env:LLM_PROVIDER="qwen"
$env:DASHSCOPE_API_KEY="<your-dashscope-api-key>"
$env:QWEN_MODEL="qwen-plus"
docker compose up --build -d
```

真实 Key 只通过运行环境注入，不写入代码、文档或测试。

## 4. Redis 配置

Docker Compose 默认注入 `REDIS_URL=redis://redis:6379/0`，用于 `/health/ready` Redis 就绪检查、流式追问 Token 服务端短期存储、JWT 黑名单、登录失败限流、高成本面试接口限流、面试回答草稿、异步任务状态和 `interview.questions`/`interview.follow_up`/`interview.report` 队列；`/health/ready` 也会返回 `interview_worker_queue` 与 `llm_gateway` 状态，用于确认 worker 队列和 mock/Qwen provider 配置是否就绪。

默认接口限流配置：

```powershell
$env:API_RATE_LIMIT_PER_MINUTE="30"
$env:API_RATE_LIMIT_WINDOW_SECONDS="60"
docker compose up --build -d
```

默认面试草稿 TTL 为 24 小时：

```powershell
$env:INTERVIEW_DRAFT_TTL_SECONDS="86400"
$env:INTERVIEW_TASK_TTL_SECONDS="86400"
$env:INTERVIEW_TASK_QUEUE_BACKEND="redis"
$env:INTERVIEW_TASK_QUEUE_NAME="queue:interview_tasks"
docker compose up --build -d
```

Docker Compose 会启动 `worker` 服务并执行 `python -m app.workers.interview_worker` 消费 Redis 队列。本地非 Docker 启动时如果不配置 `REDIS_URL` 或保持 `INTERVIEW_TASK_QUEUE_BACKEND=background`，系统会保留进程内 BackgroundTasks 回退模式，方便开发和测试；企业部署建议始终配置 Redis 队列和独立 worker。

## 5. 停止和重启

停止容器但保留 PostgreSQL 和 Redis 数据：

```powershell
docker compose down
```

重新启动：

```powershell
docker compose up -d
```

只有确认要清空本地数据库时才执行：

```powershell
docker compose down -v
```

## 6. 端口和数据

- `8100`：FastAPI、Swagger 文档和 `/web/` 前端页面
- PostgreSQL 不暴露到宿主机，只在 Docker 网络内部访问
- Redis 不暴露到宿主机，只在 Docker 网络内部访问
- PostgreSQL 数据保存在 `ai-interviewer-postgres-data` volume，普通重启不会丢失用户和面试会话数据
- Redis 数据保存在 `ai-interviewer-redis-data` volume，普通重启不会丢失短期运行态数据
