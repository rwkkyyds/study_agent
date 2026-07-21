# 学习计划 Learning Plan

## 整体阶段成长目标

- 第1-2周：掌握 RAG 全链路（含Milvus），能独立搭建文档问答系统
- 第3-4周：掌握 LangGraph + MCP + PostgreSQL + pgvector + Redis + Celery/RabbitMQ
- 第5-6周：掌握 React 前端 + JWT 认证 + OpenTelemetry + Docker 部署 + LangGraph 高级工作流 + Agent SDK 生态
- 第7-8周：完成2个全栈工业级项目（React+FastAPI+LangGraph+Milvus+Redis+PostgreSQL+Docker），掌握系统设计面试

---

## 第1周：大模型应用开发基础 + 手撕 Naive RAG

**本周目标：** 跑通 FastAPI + LangChain + RAG 全链路，产出一个可运行的文档问答 Demo。

| 天数 | 小节 | 内容 | 预估时长 |
|------|------|------|----------|
| Day1 | Section_1 | FastAPI 路由、异步I/O、Pydantic 数据校验 | 40min |
| Day2 | Section_2 | LangChain 核心组件、Prompt Templates、Output Parsers、LCEL | 50min |
| Day3 | Section_3 | RAG 文档加载、多格式文本分块策略 | 40min |
| Day4 | Section_4 | Embedding 原理、FAISS/Chroma 本地向量库使用 | 40min |
| Day5-6 | Section_5 | 整合 FastAPI+LangChain 手撕端到端 Naive RAG | 60min |
| Day7 | Section_6 | RAG 项目 Docker 打包部署、周Demo复盘 | 50min |

**本周Demo：** 端到端 Naive RAG 文档问答系统（FastAPI + LangChain + Chroma）

---

## 第2周：Advanced RAG 与生产级向量数据库

**本周目标：** 掌握混合检索、重排、自动化评估，升级 RAG 系统至生产级。

| 天数 | 小节 | 内容 | 预估时长 |
|------|------|------|----------|
| Day8 | Section_1 | Query Transformation（HyDE、多查询改写） | 40min |
| Day9 | Section_2 | 混合检索 BM25+向量检索 + Rerank 重排 | 50min |
| Day10-11 | Section_3 | RAGAs、DeepEval RAG 自动化评估体系 | 60min |
| Day12 | Section_4 | Docker 部署 Milvus 生产级向量库 + Python SDK | 50min |
| Day13 | Section_5 | Unstructured/MinerU 复杂PDF表格/图片解析 | 40min |
| Day14 | Section_6 | 升级RAG系统，集成混合检索+重排+Milvus、周Demo | 60min |

**本周Demo：** 生产级 RAG 系统（混合检索 + Rerank + Milvus + 自动评估）

---

## 第3周：Agent 开发与 Tool Calling

**本周目标：** 掌握 Agent 核心范式 + LangGraph工作流 + MCP协议，能独立开发工具调用型智能体。

| 天数 | 小节 | 内容 | 预估时长 |
|------|------|------|----------|
| Day15 | Section_1 | Agent核心概念、ReAct框架、思考-行动工作流（已完成） | 40min |
| Day16 | Section_2 | LangGraph 核心概念、StateGraph、节点与边、条件路由 | 50min |
| Day17 | Section_3 | 自定义工具开发、MCP协议与三大MCP Server实战（Filesystem/GitHub/Playwright） | 50min |
| Day18 | Section_4 | PostgreSQL基础（数据模型设计、索引、事务、Explain Analyze、SQLAlchemy、Alembic迁移） | 50min |
| Day19 | Section_5 | Agent Memory 记忆机制、会话持久化（Redis会话存储） | 40min |
| Day20 | Section_6 | Agent工具调用异常处理、重试与降级策略 | 40min |
| Day21 | Section_7 | 搭建RAG+联网搜索研究助手Agent（集成SQL Agent）、周Demo | 60min |

**本周Demo：** RAG + LangGraph + MCP + SQL Agent 研究助手

---

## 第4周：系统性能优化与数据层

**本周目标：** 掌握 Redis 工程化、PostgreSQL 进阶、pgvector、Celery + RabbitMQ，系统 QPS 提升 3-5 倍。

| 天数 | 小节 | 内容 | 预估时长 |
|------|------|------|----------|
| Day22 | Section_1 | Redis工程化（缓存+会话存储+限流+Pub/Sub） | 50min |
| Day23 | Section_2 | PostgreSQL进阶（索引优化+连接池+性能调优） | 50min |
| Day24 | Section_3 | pgvector向量扩展（向量字段、向量索引、混合检索、PostgreSQL+pgvector RAG） | 50min |
| Day25 | Section_4 | FastAPI 异步改造、asyncio 高并发 | 50min |
| Day26 | Section_5 | Celery 异步任务队列 + RabbitMQ消息队列基础（Producer/Consumer/Exchange/Queue、消息丢失与重试） | 50min |
| Day27 | Section_6 | Embedding/Reranker 批处理优化吞吐 | 40min |
| Day28 | Section_7 | Locust压测、QPS/P99指标量化优化、周Demo | 50min |

**本周Demo：** 高性能 RAG 服务（Redis工程化 + PostgreSQL + pgvector + Celery + RabbitMQ + 压测报告）

---

## 第5周：前端、认证、监控与部署

**本周目标：** 掌握 React 前端 + JWT 认证 + 全套可观测性 + Docker 部署。

| 天数 | 小节 | 内容 | 预估时长 |
|------|------|------|----------|
| Day29 | Section_1 | React前端基础、AI Chat UI组件开发 | 50min |
| Day30 | Section_2 | React前端进阶、流式输出SSE集成 | 50min |
| Day31 | Section_3 | OAuth2.0/JWT认证、FastAPI安全中间件 | 50min |
| Day32 | Section_4 | LangSmith链路追踪、OpenTelemetry可观测性基础 | 50min |
| Day33 | Section_5 | Prometheus 监控、业务/系统指标暴露 | 50min |
| Day34 | Section_6 | Grafana 监控大盘可视化搭建 | 40min |
| Day35 | Section_7 | Docker规范+Compose多服务编排、周Demo | 50min |

**本周Demo：** 全栈 AI 应用（React前端 + JWT认证 + Prometheus + Grafana + Docker Compose）

---

## 第6周：多智能体与高级Agent架构

**本周目标：** 掌握 LangGraph 高级工作流 + Agent SDK 生态 + 多智能体设计模式。

| 天数 | 小节 | 内容 | 预估时长 |
|------|------|------|----------|
| Day36 | Section_1 | LangGraph高级工作流（条件分支、并行执行、子图） | 50min |
| Day37 | Section_2 | LangGraph Human-in-the-Loop、检查点与状态恢复 | 50min |
| Day38 | Section_3 | Agent SDK生态（Claude Code SDK、OpenAI Agents SDK、PydanticAI、MCP生态）——不绑定单一框架，学底层思想 | 50min |
| Day39 | Section_4 | AutoGen/CrewAI框架对比选型（压缩1天，了解即可） | 40min |
| Day40 | Section_5 | 多智能体系统设计模式、异常处理与容错、周Demo | 50min |

**本周Demo：** LangGraph 多智能体协作系统（带Human-in-the-Loop + 容错）

---

## 第7-8周：工业级项目实战 + 简历面试冲刺

**本周目标：** 完成2个全栈工业级项目，提炼简历亮点，冲刺面试。

| 天数 | 内容 | 预估时长 |
|------|------|----------|
| Day41-45 | 项目一后端：企业级智能客服RAG系统（FastAPI+LangGraph工作流+Milvus强制使用+Redis+PostgreSQL+SQL Agent） | 5天 |
| Day46-49 | 项目一前端+部署：React前端+JWT认证+Prometheus监控+Docker Compose部署+项目文档 | 4天 |
| Day50-53 | 项目二后端：AI面试官系统（简历解析→生成题目→AI面试→评分→报告生成，LangGraph+RAG+Agent+Redis+PostgreSQL） | 4天 |
| Day54-57 | 项目二前端+部署：React前端+SSE流式输出+JWT认证+Docker部署 | 4天 |
| Day58 | 系统设计面试（百万用户聊天系统设计、RAG扩容、Milvus分片、Redis高可用、Agent任务调度） | 1天 |
| Day59-60 | 项目总结、量化亮点写入简历、LLM系统设计刷题、模拟面试 | 2天 |

**本周Demo：**
- 项目一：企业级智能客服 RAG 系统（全栈：React + FastAPI + LangGraph + Milvus + Redis + PostgreSQL + Docker）
- 项目二：AI 面试官系统（全栈：React + FastAPI + LangGraph + RAG + SSE + JWT + PostgreSQL）
