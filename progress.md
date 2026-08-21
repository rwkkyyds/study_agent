# 学习进度 Progress

| 小节 | 状态 | 完成时间 | 复习次数 | 难度评分 | 知识备注 |
|------|------|----------|----------|----------|----------|
| **第1周** | | | | | |
| Section_1_FastAPI入门 | 已完成 | 2026-05-31 | 0 | - | 路由/Pydantic/异步I/O/HTTPException |
| Section_2_LangChain核心 | 已完成 | 2026-05-31 | 0 | - | Prompt Template/Output Parser/LCEL |
| Section_3_RAG文档分块 | 已完成 | 2026-06-01 | 0 | - | Document Loader/TextSplitter/chunk_size/overlap |
| Section_4_Embedding与向量库 | 已完成 | 2026-06-01 | 0 | - | Embedding/余弦相似度/向量库/RAG检索链路 |
| Section_5_端到端NaiveRAG | 已完成 | 2026-06-02 | 0 | - | RAG链路整合/LangChain组件化/FastAPI封装/LCEL链 |
| Section_6_Docker部署与复盘 | 已完成 | 2026-06-03 | 0 | - | Dockerfile/镜像构建/容器部署/第1周Demo |
| **第2周** | | | | | |
| Section_1_QueryTransformation | 已完成 | 2026-06-03 | 0 | - | HyDE/多查询改写/fastembed+BGE本地Embedding/FAISS |
| Section_2_混合检索与重排 | 已完成 | 2026-06-03 | 0 | - | BM25/RRF融合/Rerank重排/两阶段检索架构 |
| Section_3_RAG评估体系 | 已完成 | 2026-06-04 | 0 | - | RAGAs/DeepEval/Faithfulness/Context Precision/Context Recall |
| Section_4_Milvus向量库 | 已完成 | 2026-06-09 | 0 | - | Milvus Docker部署/pymilvus新API/VectorStore适配器/HNSW索引 |
| Section_5_复杂文档解析 | 已完成 | 2026-06-09 | 0 | - | pdfplumber表格提取/PyMuPDF/结构化解析/表格转Markdown/RAG集成 |
| Section_6_升级RAG系统 | 已完成 | 2026-06-10 | 0 | - | Advanced RAG集成/混合检索/RRF融合/Rerank/FlashRank/Docker部署 |
| **第3周** | | | | | |
| Section_1_Agent与ReAct | 已完成 | 2026-06-11 | 0 | - | Agent本质/ReAct框架/@tool装饰器/create_agent新API/推理循环 |
| Section_2_LangGraph核心 | 已完成 | 2026-06-12 | 0 | - | StateGraph/Node/Edge/ConditionalEdge/AgentNode/ToolNode/should_continue循环 |
| Section_3_MCP协议实战 | 已完成 | 2026-06-12 | 0 | - | MCP协议/Server创建/Client连接/stdio传输/JSON-RPC/MCP+LangGraph集成 |
| Section_4_PostgreSQL基础 | 已完成 | 2026-06-16 | 0 | - | SQLAlchemy ORM/CRUD/事务/Model设计/FastAPI依赖注入/Pydantic↔Model转换 |
| Section_5_AgentMemory | 已完成 | 2026-06-16 | 0 | - | 短期/工作/长期记忆/MemorySaver/Checkpoint/thread_id隔离/Redis会话存储 |
| Section_6_异常处理与降级 | 已完成 | 2026-06-17 | 0 | - | 异常捕获/tenacity重试/指数退避/Fallback工具链/三级容错/条件路由降级 |
| Section_7_研究助手Agent | 已完成 | 2026-06-18 | 0 | - | 多工具协作/搜索+检索+SQL Agent/防无限循环/Week3综合Demo |
| **第4周** | | | | | |
| Section_1_Redis工程化 | 已完成 | 2026-06-19 | 0 | - | Cache-Aside/会话存储/滑动窗口限流/Pub-Sub/缓存穿透击穿雪崩 |
| Section_2_PostgreSQL进阶 | 已完成 | 2026-06-27 | 0 | - | 索引优化/连接池/EXPLAIN ANALYZE/N+1/窗口函数/CTE |
| Section_3_pgvector向量扩展 | 已完成 | 2026-06-30 | 0 | ⭐⭐⭐ | Vector(512)/IVFFlat/HNSW/混合检索/RRF/pgvector RAG/Docker pg17 |
| Section_4_异步高并发 | 已完成 | 2026-07-06 | 0 | ⭐⭐ | async/await/协程/gather/create_task/FastAPI async def/run_in_executor/async SQLAlchemy |
| Section_5_Celery_RabbitMQ | 已完成 | 2026-07-06 | 0 | ⭐⭐⭐ | Celery架构/重试退避/chain/group/chord/FastAPI集成/RabbitMQ概念 |
| Section_6_批处理优化 | 已完成 | 2026-07-11 | 0 | ⭐⭐ | Embedding/Reranker批处理/Pipeline批量化/吞吐量优化 |
| Section_7_压测与量化 | 已完成 | 2026-07-11 | 0 | ⭐⭐ | Locust压测/P50-P90-P99/QPS/缓存优化量化/RAG系统压测/瓶颈定位 |
| **第5周** | | | | | |
| Section_1_React前端基础 | 未学习 | - | 0 | - | 用户要求暂时跳过前端知识 |
| Section_2_React流式SSE | 未学习 | - | 0 | - | 用户要求暂时跳过前端知识 |
| Section_3_JWT认证 | 已完成 | 2026-07-19 | 0 | ⭐⭐ | OAuth2.0/JWT认证、FastAPI安全中间件/Bearer Token/角色权限 |
| Section_4_LangSmith与OTel | 已完成 | 2026-07-20 | 0 | ⭐⭐ | LangSmith链路追踪/OpenTelemetry span/FastAPI请求观测 |
| Section_5_Prometheus监控 | 已完成 | 2026-07-22 | 0 | ⭐⭐ | Prometheus真实指标暴露/Counter/Gauge/Histogram/FastAPI metrics |
| Section_6_Grafana大盘 | 已完成 | 2026-08-03 | 0 | ⭐⭐ | Grafana定位/大盘三要素/PromQL/Provisioning自动导入/P95分位/可视化链路 |
| Section_7_Docker部署 | 未学习 | - | 0 | - | - |
| **第6周** | | | | | |
| Section_1_LangGraph高级工作流 | 已完成 | 2026-07-31 | 0 | ⭐⭐⭐ | 并行审查工作流/条件路由工单分流/子图订单管线/StateGraph编译 |
| Section_2_LangGraph HITL | 已完成 | 2026-07-31 | 0 | ⭐⭐ | interrupt暂停/Command恢复/退款审批工作流/编辑后发送 |
| Section_3_Agent_SDK生态 | 已完成 | 2026-07-31 | 0 | ⭐⭐ | OpenAI Agents SDK/Pydantic-AI结构化输出/MCP工具形状/通用运行时 |
| Section_4_AutoGen_CrewAI对比 | 已完成 | 2026-07-30 | 0 | ⭐⭐ | 对话驱动vs任务驱动/GroupChat/speaker策略/kickoff流水线/context依赖 |
| Section_5_多智能体设计模式 | 已完成 | 2026-08-01 | 0 | ⭐⭐⭐ | 分层/对等/流水线三模式/超时重试降级熔断四层容错/第6周综合Demo |
| **第7-8周** | | | | | |
| 项目一_智能客服后端 | 已完成 | 2026-08-15 | 0 | ⭐⭐⭐⭐ | 已完成全栈智能客服 RAG 系统：FastAPI、Next.js、JWT、RBAC、Milvus、Redis、PostgreSQL、Docker、知识库、工单转人工、SSE、测试与面试文档 |

| 项目二_AI面试官后端 | 学习中 | 2026-08-21 | 0 | ⭐⭐⭐⭐ | 阶段一至五已完成：项目骨架、JWT认证、SQLAlchemy落库、Alembic迁移、简历解析、岗位画像、LangGraph面试工作流、追问持久化、RAG题库检索、测试与阶段文档 |
| 项目二_AI面试官前端部署 | 未学习 | - | 0 | - | - |
| 系统设计面试 | 未学习 | - | 0 | - | - |
| 简历与模拟面试 | 未学习 | - | 0 | - | - |
