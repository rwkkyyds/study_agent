# 项目一：企业级智能客服 RAG 系统

## 项目定位

这是第 7-8 周的工业级项目，目标是把前 6 周学习的 RAG、Agent、数据层、性能优化、可观测性和容错能力整合为可运行、可测试、可部署的企业级智能客服系统。

当前项目已经包含 FastAPI 后端、React/Next.js 前端、PostgreSQL、Redis 和本地 Docker Compose 启动流程，可直接通过浏览器体验登录、知识库、智能客服和工单功能。

## 详细文档

请从 [项目文档目录](docs/README.md) 开始阅读。每个阶段完成后必须同时交付代码、测试和对应阶段文档。

## 本地 Docker 快速启动

```powershell
docker compose up --build -d
docker compose exec app python scripts/create_admin.py --username admin --password admin123 --role admin
```

然后访问 http://localhost:3000，用 `admin / admin123` 登录。更完整的启动、账号和排错步骤见 [本地 Docker 启动与使用指南](DOCKER_RUN.md)。

## 当前能力

- FastAPI、Pydantic、异常处理和日志
- React/Next.js 前端页面与本地 Docker 访问入口
- SQLAlchemy 数据模型与 JWT 认证
- Mock Embedding、文本分块、向量检索内核
- 前 6 周已学习的 LangGraph、Milvus、Redis、容错和可观测性知识

## 阶段进度

- 阶段一：项目骨架，已完成
- 阶段二：身份认证与数据层，已完成
- 阶段三：知识库入库与检索，已完成
- 阶段四：客服 LangGraph 工作流，已完成
- 阶段五：企业级稳定性，已完成
- 阶段六：容器化与部署，已完成


## 运行验证

```powershell
python -m pytest tests/ -v
```
