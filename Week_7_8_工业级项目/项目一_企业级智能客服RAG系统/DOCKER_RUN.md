# 本地 Docker 启动与使用指南

## 1. 启动

在项目根目录执行：

```powershell
cd "C:\Users\admin\Desktop\agent_study\Week_7_8_工业级项目\项目一_企业级智能客服RAG系统"
docker compose up --build -d
```

启动后访问：

- 前端页面：http://localhost:3000
- 后端接口：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 2. 查看状态和日志

```powershell
docker compose ps
docker compose logs -f app
docker compose logs -f frontend
```

如果只想看最近日志：

```powershell
docker compose logs --tail=100 app
```

## 3. 创建初始管理员

第一次启动后，需要创建一个 admin 账号，才能进入用户管理页面创建客服账号：

```powershell
docker compose exec app python scripts/create_admin.py --username admin --password admin123 --role admin
```

如果提示用户名已存在，说明账号已经创建过，可以直接登录。

然后打开 http://localhost:3000/login，用 `admin / admin123` 登录。这个密码仅适合本地学习环境，正式演示或部署前请改成强密码。

## 4. 典型使用流程

1. 用管理员账号登录。
2. 进入“用户管理”，创建一个 `agent` 客服账号。
3. 进入“知识库”，上传一段 FAQ 或业务说明。
4. 进入“智能客服”，提问刚才上传的内容。
5. 输入“请转人工”，系统会创建工单。
6. 进入“我的工单”查看工单状态。

## 5. 停止和重启

停止容器但保留数据库数据：

```powershell
docker compose down
```

重新启动：

```powershell
docker compose up -d
```

如果要彻底清空本地数据库和 Redis 数据，才使用：

```powershell
docker compose down -v
```

## 6. 端口说明

本地只暴露两个入口：

- `3000`：前端页面
- `8000`：后端 API

PostgreSQL 和 Redis 不暴露到宿主机，只在 Docker 网络内部给后端访问，因此不会和你电脑已有的 5432/6379 冲突。

## 7. DashScope 说明

如果 `.env` 中设置了 `DASHSCOPE_API_KEY`，容器会使用真实通义千问 Embedding 和 LLM。
如果不设置，系统会回退到本地 Mock Embedding，适合先跑通项目流程。
