# 项目一：企业级智能客服 RAG 系统

## 项目定位

这是第7-8周的第一个工业级项目，目标是把前6周已经学习的 RAG、Agent、数据层、性能优化、可观测性和容错能力，整合成一个可运行、可测试、可部署的企业级智能客服后端。

当前阶段优先实现后端。React 前端基础和 SSE 按当前学习约束暂时跳过，不阻塞后端项目推进，后续通过 API 文档和接口测试保证前端可以接入。

## 详细文档

每个阶段的完整设计文档、代码说明、架构图和请求流程，请查看：

👉 **[项目文档目录](docs/README.md)**

```
docs/
├── README.md                          # 文档索引
├── 01-项目总览/                        # 项目定位、技术栈、路线图
│   ├── README.md                      # 项目概述
│   ├── 目录结构.md                     # 完整目录树 + 文件说明
│   └── 实施路线图.md                    # 6 个阶段目标
└── 02-阶段一_项目骨架/                  # 阶段一：项目初始化
    ├── README.md                      # 阶段一概述
    ├── 01-应用入口.md                  # main.py 详解
    ├── 02-配置管理.md                  # config.py 详解
    ├── 03-数据库会话.md                # session.py 详解
    ├── 04-接口与测试.md                # health/version + test
    ├── 05-项目脚手架说明.md             # 目录结构、运行方式
    └── 06-请求流程.md                  # 请求生命周期
```

## 已具备能力

- FastAPI、Pydantic、异常处理和日志
- LangChain、LangGraph、ReAct、Tool Calling
- Naive RAG、Advanced RAG、混合检索、Rerank
- Milvus 向量库，项目中强制使用
- PostgreSQL、SQLAlchemy、事务、索引和 SQL Agent
- Redis 缓存、会话记忆和限流
- Celery、RabbitMQ、异步任务和批处理
- JWT 认证、角色权限
- OpenTelemetry、Prometheus、Grafana 基础
- LangGraph HITL、多智能体工作流、重试、超时、熔断和降级

## 当前限制与处理方式

| 项目 | 当前状态 | 项目处理方式 |
|------|----------|--------------|
| React 前端基础 | 暂时跳过 | 先完成后端 API、OpenAPI 和接口测试，前端放到后续阶段 |
| React SSE | 暂时跳过 | 第一版提供普通问答接口；流式接口作为后续增强项 |
| Grafana 大盘 | ✅ 已完成 | 学习笔记+面试题已生成，项目阶段五会集成 Prometheus 指标 |
| Docker Compose | 尚未完成 | 后端本地运行优先，基础服务 Compose 化作为项目部署阶段（阶段六） |
| 外部 LLM/API Key | 可能不可用 | 所有核心链路保留 mock/本地测试替身，禁止把密钥写入仓库 |

## 项目目标

第一版完成后端骨架上认证闭环：

1. FastAPI 应用可启动，生命周期管理
2. 环境变量配置通过 Pydantic Settings 集中管理
3. SQLite 数据库会话（SQLAlchemy 2.0）
4. 健康检查 + 版本号接口
5. JWT 用户注册、登录、身份校验
6. 角色权限系统（admin/agent/customer）
7. 数据模型（User/Document/Ticket/Message）
8. pytest 覆盖核心接口
9. 目录结构为后续 PostgreSQL、Redis、Milvus 和 LangGraph 接入预留清晰边界

## 当前目录结构

```text
项目一_企业级智能客服RAG系统/
├── README.md
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py                     # FastAPI 入口
│   ├── core/config.py              # 配置管理
│   ├── db/session.py               # 数据库会话
│   ├── models/                     # 数据模型（User/Document/Ticket/Message）
│   ├── schemas/                    # Pydantic 请求/响应模型
│   ├── services/auth.py            # 认证服务
│   └── api/auth.py                 # 认证 API
├── tests/
│   ├── test_health.py              # 健康检查测试
│   └── test_auth.py                # 认证测试
├── docs/                           # 项目文档
│   ├── 01-项目总览/
│   └── 02-阶段一_项目骨架/
└── .gitignore
```

## 当前进度

### 阶段一：项目骨架和可运行健康检查 ✅ 已完成

- 创建 FastAPI 应用入口
- 配置环境变量和日志
- 添加健康检查与版本接口
- 建立 pytest 测试基线

### 阶段二：身份认证与业务数据层 ✅ 已完成

- 数据模型：User、Document、Chunk、Ticket、Message
- JWT 登录、角色权限和审计字段
- 注册/登录/用户信息 API

### 阶段三：知识库入库与检索 ⏳ 待开始

- MockEmbedding（本地嵌入，无需 API Key）
- InMemoryVectorStore（内存向量存储）
- TextChunker（文档切分）
- Retriever（查询 → 嵌入 → 搜索）

### 后续阶段 ⏳ 待开始

阶段四至六将在前三个阶段完成后逐步推进。

## 验证方式

```powershell
# 运行全部测试
python -m pytest tests/ -v
# 预期：10 passed（2 health + 8 auth）
```

## 学习方式

每个项目切片遵循：先运行代码，再解释设计，再补测试和项目文档。每次只推进一个可验证切片，避免一次生成无法理解和无法排错的大型代码。
