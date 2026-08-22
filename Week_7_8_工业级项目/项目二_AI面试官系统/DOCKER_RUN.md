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
docker compose logs -f app
```

只看最近日志：

```powershell
docker compose logs --tail=100 app
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

## 4. 停止和重启

停止容器但保留 PostgreSQL 数据：

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

## 5. 端口和数据

- `8100`：FastAPI、Swagger 文档和 `/web/` 前端页面
- PostgreSQL 不暴露到宿主机，只在 Docker 网络内部访问
- PostgreSQL 数据保存在 `ai-interviewer-postgres-data` volume，普通重启不会丢失用户和面试会话数据
