# 项目概述

## 项目定位

企业级智能客服 RAG 系统，是一个面向企业知识库和客服工单场景的后端服务。

它整合了前 6 周已学习的 RAG、Agent、数据层、性能优化、可观测性和容错能力，形成一个可运行、可测试、可部署的生产级后端。

## 技术栈

| 层 | 技术选型 | 说明 |
|----|----------|------|
| Web 框架 | FastAPI | 异步路由、Pydantic 校验、自动 OpenAPI |
| ORM | SQLAlchemy 2.0 | 声明式模型、异步支持、迁移 |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） | 本地零配置，生产切换 |
| 向量库 | Milvus（生产）/ InMemory（开发） | 生产级向量检索 |
| 缓存 | Redis（可选） | 会话记忆、限流 |
| 认证 | JWT + SHA-256 | 无状态认证，角色权限 |
| 工作流 | LangGraph | 客服流程编排、状态机、HITL |
| 嵌入 | MockEmbedding（本地）/ fastembed（生产） | 无需外部 API Key |
| 可观测性 | Prometheus + Grafana | 指标暴露、监控大盘 |
| 测试 | pytest | 单元测试、API 测试 |

## 核心约束

| 约束 | 处理方式 |
|------|----------|
| 无外部 LLM API Key | 所有链路保留 Mock 本地替身，不写密钥到仓库 |
| 无 Docker Compose | 阶段一至四本地运行优先，阶段六容器化 |
| SQL Agent 安全性 | 只能通过受控工具访问数据，禁止直接执行 SQL |
| 前端跳过 | 先完成后端 API 和接口测试，前端后续接入 |

## 项目结构

```
项目一_企业级智能客服RAG系统/
├── app/                     # 应用核心代码
│   ├── main.py              # FastAPI 入口 + 路由注册
│   ├── core/                # 配置管理
│   ├── db/                  # 数据库会话
│   ├── models/              # SQLAlchemy 数据模型
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── services/            # 业务逻辑服务
│   ├── api/                 # API 路由
│   ├── rag/                 # RAG 检索模块
│   └── agent/               # LangGraph 客服工作流
├── tests/                   # pytest 测试
├── docs/                    # 项目文档（本文档）
├── data/                    # 数据文件（可选）
├── migrations/              # Alembic 迁移（可选）
├── requirements.txt         # 依赖清单
├── .env.example             # 环境变量模板
└── README.md                # 项目 README
```

## 用户故事

1. 用户登录系统，获取 JWT token
2. 管理员上传企业知识库文档
3. 文档自动解析、切分、向量化、入库
4. 用户提问，系统执行 LangGraph 客服工作流
5. 工作流判断意图，检索知识库或查询订单
6. 复杂问题自动转人工客服
7. 系统监控请求量、错误率、耗时