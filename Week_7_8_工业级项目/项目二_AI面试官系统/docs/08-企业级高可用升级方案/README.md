# 阶段八：企业级高可用升级方案

目标：把当前 AI 面试官系统从“可演示的工业级学习项目”升级为“可真实落地的高可用企业级 AI 面试平台”。升级重点不是简单堆技术，而是让前台候选人端、后台 HR/面试官端、AI 工作流、数据持久化、异步任务、监控告警和部署运维形成稳定闭环。

## 1. 当前项目现状判断

当前项目已经具备一条完整业务链路：

    注册/登录
    -> 简历文本或文件解析
    -> 候选人画像
    -> 岗位题库检索
    -> 面试题生成
    -> 候选人回答
    -> SSE 流式追问
    -> 多维度评分报告
    -> 前端看板和历史会话

已经形成的工程能力：

| 方向 | 已具备能力 | 代码位置 |
| --- | --- | --- |
| API 服务 | FastAPI 路由、依赖注入、CORS、静态前端托管 | app/main.py |
| 认证权限 | bcrypt 密码哈希、JWT、角色依赖、用户归属校验 | app/services/auth.py |
| 数据持久化 | SQLAlchemy 模型、Alembic 迁移、会话/题目/回答/报告落库 | app/models/、alembic/ |
| AI 面试闭环 | 简历解析、岗位画像、题库检索、追问、评分、报告 | app/workflow/interview_graph.py |
| 流式体验 | 短期 stream token + SSE 事件流 | app/api/interviews.py |
| 前端后台 | Vue3 + Element Plus + ECharts 看板、会话、工作台 | frontend/src/ |
| 容器部署 | Dockerfile、docker-compose、PostgreSQL healthcheck | Dockerfile、docker-compose.yml |

要达到企业级真实落地，还存在这些核心差距：

| 差距 | 当前状态 | 企业级要求 |
| --- | --- | --- |
| 高可用 | 单 app + 单 PostgreSQL，缺 Redis/MQ/副本/熔断 | 多实例 API、Redis 缓存、MQ 异步任务、失败重试、降级 |
| AI 真实性 | 默认规则链路，Qwen 只是可选增强 | LLM Gateway、Prompt 版本、调用追踪、评估集、成本控制 |
| RAG 深度 | 本地关键词题库，不是真向量检索 | 文档入库、Embedding、Vector DB、Rerank、引用溯源 |
| Agent 编排 | 本地 state-node 模拟 LangGraph 思路 | 真 LangGraph、checkpoint、条件边、工具节点、人工介入 |
| 前台业务 | 候选人面试体验已有雏形 | 完整候选人门户、预约、设备检查、进度保存、报告查看 |
| 后台业务 | 面试官看板和历史会话已有基础 | HR 多角色、岗位/JD/题库/候选人/批次/报告/审核全流程 |
| 运维观测 | 有 health/ready，缺指标、日志、告警 | Prometheus、Grafana、OTel、结构化日志、审计日志 |
| 安全合规 | 基础 JWT，缺刷新、黑名单、审计、数据脱敏 | Refresh Token、RBAC/ABAC、PII 脱敏、操作审计、限流 |

## 2. 企业级目标架构

推荐目标架构：

    Browser
    -> Candidate Portal / HR Console
    -> Nginx / CDN
    -> FastAPI API Gateway
    -> Auth/User Service + Interview API + Admin/Report API
    -> Domain Service Layer
    -> PostgreSQL + Redis + Message Queue
    -> AI Workflow Workers
    -> LLM Gateway + RAG Service + Evaluation
    -> Logs + Metrics + Traces + Alerts

本机环境可以这样映射：

| 本机组件 | 建议用途 | 项目配置方式 |
| --- | --- | --- |
| PostgreSQL | 主业务库：用户、岗位、简历、会话、报告、审计 | DATABASE_URL=postgresql+psycopg://... |
| Redis | 缓存、限流、短期 token、会话草稿、任务状态 | 新增 REDIS_URL=redis://localhost:6379/0 |
| MQ | AI 任务队列：简历解析、题目生成、评分报告、通知 | RabbitMQ 用 AMQP_URL，或 Redis Stream/RQ 简化 |
| Docker Desktop | 本地 Compose 一键启动 app/postgres/redis/mq/worker | 扩展 docker-compose.yml |
| Clash Verge 7897 | LLM API 外网代理 | HTTP_PROXY=http://127.0.0.1:7897，HTTPS_PROXY=http://127.0.0.1:7897 |

## 3. 后端升级方案

### 3.1 认证与组织权限

原先只有 candidate/admin 两类角色；阶段二已先扩展 candidate/interviewer/hr/admin 角色，并补齐 RBAC 数据底座。企业级系统建议继续升级为：

    Tenant
    -> Organization
    -> User
    -> Role
    -> Permission
    -> Resource Ownership

建议角色：

| 角色 | 权限 |
| --- | --- |
| candidate | 完成面试、查看自己的面试记录和报告 |
| interviewer | 查看分配给自己的候选人、发起追问、补充人工评价 |
| hr | 管理岗位、候选人、面试批次、报告流转 |
| admin | 管理组织、用户、题库、系统配置 |

阶段二已新增其中认证权限底座；后端后续还需要继续完善：

- organizations：组织/租户表（已建表）
- roles、permissions：权限表（已建表）
- user_roles：用户角色关系（已建表）
- audit_logs：关键操作审计（已建表并接入认证操作）
- Refresh Token：避免 access token 长期有效（已接入登录/刷新）
- Redis Token 黑名单：支持退出登录和强制下线（已接入 logout/refresh 轮换）
- 登录失败次数限制：防暴力破解（已接入登录接口）
- 多角色权限依赖：支持 HR/Admin/Interviewer 复用后台业务域接口权限边界（已接入 `/hiring/*`）

### 3.2 面试业务域建模

当前核心对象是面试会话。真实招聘系统还需要把业务前置对象补齐：

    岗位 JD
    -> 招聘批次
    -> 候选人
    -> 简历版本
    -> 面试邀请
    -> 面试会话
    -> AI 报告
    -> 人工复核
    -> 录用建议

建议新增表：

| 表 | 作用 |
| --- | --- |
| jobs | 岗位名称、级别、JD、技能要求、评分维度 |
| candidate_profiles | 候选人基础信息、联系方式、标签、来源 |
| interview_batches | 校招/社招/岗位批次管理 |
| interview_invites | 邀请链接、有效期、候选人进入状态 |
| evaluation_rubrics | 评分标准和权重版本 |
| manual_reviews | 面试官人工复核意见 |
| notification_logs | 邮件/短信/站内通知记录 |

当前已启动 3.2 第一批落地：

- 已新增 `jobs`、`candidate_profiles`、`interview_batches`、`interview_invites`、`evaluation_rubrics`、`manual_reviews`、`notification_logs` ORM 模型和 Alembic 迁移。
- 已给 `interview_sessions` 增加 `job_id`、`candidate_profile_id`、`interview_batch_id`、`invite_id`、`rubric_id` 可选业务外键，保持旧链路兼容。
- 已新增 `/hiring/*` 最小后台 API，覆盖岗位、候选人、批次、邀请、评分标准、人工复核、通知日志。
- 已补外键列和常用筛选列索引，并对邀请有效期场景增加 PostgreSQL partial index。
- 已打通邀请启动面试：`POST /interviews/questions` 支持 `invite_token`，自动绑定岗位、候选人、批次、有效评分标准，并把会话写回 `interview_sessions` 业务外键。
- 已增加邀请重复消费保护：同一 `invite_token` 创建会话后再次启动返回 409，避免候选人刷新造成重复面试会话。
- 已接入候选人前台入口：`/web/?invite_token=<token>` 会进入邀请落地页，展示岗位、候选人脱敏信息和有效期，登录后可直接启动绑定邀请的面试。
- 已补齐 rubric 权重评分：报告生成时会读取会话绑定的 `evaluation_rubrics.dimensions/weights`，按岗位评分标准重算总分；未绑定 rubric 时保持默认评分权重。

### 3.3 Redis 接入

Redis 不要只作为“缓存”口号，要绑定具体场景：

| 场景 | Redis 设计 |
| --- | --- |
| 短期 stream token | stream_token:{jti}，TTL 5 分钟，用完即删 |
| 登录黑名单 | jwt:blacklist:{jti}，TTL 到 token 过期 |
| API 限流 | rate:{user_id}:{route}:{minute} |
| 面试草稿 | draft:{session_id}:{question_id}，TTL 24 小时 |
| AI 任务状态 | task:{task_id}，记录 queued/running/succeeded/failed |
| 热点题库缓存 | question_bank:{job_id}:{difficulty} |

优先实现顺序：

1. 接入 Redis 客户端和健康检查。
2. 把 SSE stream token 从 JWT 内承载 answer 改为 Redis 短 token，仅 token id 放到 URL。
3. 加登录/接口限流。
4. 加任务状态缓存。

当前进度：1、2 已完成；3 已完成登录失败限流、高成本面试接口限流、面试草稿自动保存和 `task:{task_id}` 任务状态缓存；题库热缓存仍待后续阶段。

### 3.4 MQ 和异步任务

当前追问仍在请求/流式链路内执行；题目生成和评分报告已先接入异步任务，企业级系统应继续把高耗时 AI 链路统一异步化：

    API 接收请求
    -> 写入 interview_tasks
    -> 投递 MQ
    -> Worker 执行 LLM/RAG/评分
    -> 更新 PostgreSQL
    -> Redis 更新任务状态
    -> 前端轮询或 SSE/WebSocket 获取进度

建议任务：

| 任务 | 队列 | 为什么异步 |
| --- | --- | --- |
| 简历 PDF/OCR 解析 | resume.parse | 文件解析耗时且可能失败 |
| 简历画像生成 | resume.profile | 可能调用 LLM |
| 面试题生成 | interview.questions | RAG + LLM 延迟不可控 |
| 追问生成 | interview.follow_up | 流式体验和失败重试需要解耦 |
| 报告评分 | interview.report | 多模型/多维评分耗时 |
| 通知发送 | notification.send | 邮件短信不能阻塞主流程 |

本机有 MQ 时，推荐 RabbitMQ + Celery；如果想少引依赖，可以先用 Redis Queue/RQ/Redis List 过渡。当前已落地 Redis 队列 + 独立 Worker 第一批：`POST /interviews/questions/async` 创建 `interview.questions` 任务，`POST /interviews/follow-up/async` 创建 `interview.follow_up` 任务，`POST /interviews/evaluate/async` 创建 `interview.report` 任务，Redis 模式下都投递到 `queue:interview_tasks`，`python -m app.workers.interview_worker` 独立消费并写回任务状态；未配置 Redis 队列时保留 FastAPI BackgroundTasks 回退。候选人面试室和 HR 工作台已改为消费题目生成/追问生成/评分异步任务。通知发送和失败重试仍是下一步。

### 3.5 LLM Gateway

当前 Qwen 客户端直接写在业务服务内。企业级建议独立一层 LLM Gateway：

    业务服务
    -> LLM Gateway
       -> provider router
       -> prompt registry
       -> retry/backoff
       -> timeout
       -> circuit breaker
       -> cost tracking
       -> response validator

必须具备：

- 多模型配置：Qwen、OpenAI-compatible、本地模型。
- 代理配置：支持 HTTP_PROXY=http://127.0.0.1:7897。
- Prompt 版本化：prompt_key + version。
- 输出 JSON Schema 校验：失败自动修复或回退规则链路。

当前已完成第一批落地：新增 `app/services/llm_gateway.py`，Qwen 调用通过 Gateway 统一处理 provider 路由、环境代理继承、超时、重试、Prompt 版本标识和 JSON 对象校验；`/health/ready` 已返回 `llm_gateway` 状态。多模型 registry、成本统计、熔断和评估集仍待后续阶段。
- 调用日志：模型、tokens、耗时、错误、成本。
- 熔断降级：供应商失败时切 mock/rule fallback。

### 3.6 真 RAG 升级

当前题库是本地 Python 列表 + 关键词打分，只能算检索原型。企业级 RAG 应升级为：

    岗位 JD / 题库 / 候选人简历 / 公司面试标准
    -> 文档解析
    -> Chunk
    -> Embedding
    -> Vector DB
    -> Hybrid Search
    -> Rerank
    -> Context Builder
    -> LLM 生成
    -> 引用来源回写

建议分三步：

1. 先用 PostgreSQL + pgvector，减少本地组件数量。
2. 数据规模上来后再切 Milvus/Qdrant。
3. 后台增加“知识库管理”页面：上传 JD、题库、评分标准、版本发布。

### 3.7 观测、稳定性和安全

企业级上线前至少补：

| 能力 | 要求 |
| --- | --- |
| 日志 | JSON 结构化日志，带 request_id/user_id/session_id/task_id |
| 指标 | 请求量、错误率、延迟、LLM 成本、任务失败率、队列堆积 |
| 链路追踪 | API -> DB -> Redis -> MQ -> LLM |
| 告警 | ready 失败、错误率升高、LLM 超时、队列堆积 |
| 限流 | 登录、生成题目、追问、报告生成分级限流 |
| 数据安全 | 简历和报告属于 PII，展示脱敏、导出加水印、访问审计 |
| 备份 | PostgreSQL 定时备份，报告和简历支持恢复 |

## 4. 前台功能完善方案

前台指候选人端，目标是让候选人可以独立完成一次真实面试，而不是依赖开发者操作后台。

### 4.1 候选人核心流程

    候选人收到邀请链接
    -> 注册/登录或一次性免登录 token
    -> 阅读面试说明
    -> 设备/网络检查
    -> 上传或确认简历
    -> 选择/确认目标岗位
    -> 开始面试
    -> 逐题作答
    -> AI 实时追问
    -> 提交面试
    -> 查看候选人版反馈或等待 HR 审核

### 4.2 前台需要补的页面

| 页面 | 功能 |
| --- | --- |
| 邀请落地页 | 展示公司、岗位、面试时长、有效期、注意事项 |
| 候选人资料页 | 姓名、邮箱、手机号、简历上传、岗位确认 |
| 设备检查页 | 麦克风/摄像头/浏览器兼容/网络延迟，后续可扩展语音视频 |
| 面试进行页 | 题目、回答区、计时、进度、追问、保存草稿 |
| 中断恢复页 | 网络断开后恢复到上一题和草稿 |
| 完成页 | 提交成功、后续流程、候选人可见反馈 |
| 候选人历史页 | 查看自己的历史面试和反馈 |

### 4.3 前台和后端配合点

| 前端需要 | 后端需要提供 |
| --- | --- |
| 邀请链接进入 | GET /hiring/invites/{token}（已实现，前端 `/web/?invite_token=<token>` 已接入） |
| 候选人确认资料 | POST /candidate/profile |
| 简历上传进度 | 异步任务 ID + 任务状态 API |
| 面试草稿自动保存 | PUT /interviews/sessions/{id}/drafts（已实现，Redis key 为 `draft:{session_id}:{question_id}`） |
| 断点续面 | GET /interviews/sessions/{id}/drafts + GET /interviews/sessions/{id}（已实现基础恢复） |
| 追问流式展示 | SSE/WebSocket 统一事件协议 |
| 提交后不可篡改 | 会话状态机：created/running/submitted/reviewed |

当前前台已完成第一批落地：邀请落地页、候选人登录后回到邀请页、基于 `invite_token` 启动绑定岗位/批次/评分标准的面试、面试间回答草稿自动保存和邀请会话继续入口；入口已拆为 `/web/candidate` 与 `/web/console`，旧 `/web/?invite_token=<token>` 仍兼容。后续仍需补设备检查、完成页和候选人历史页。

后续风险补充：

- 前端已引入 Vue Router/Pinia，但还只是第一批拆分，候选人历史、岗位、批次等后续页面还需要继续沉淀到独立 store。
- 邀请异常态只有基础提示，过期邀请、已使用邀请仍需要独立体验。
- 候选人版/HR 版报告已完成基础权限分层；HR 控制台打开已评分会话时已接入后台完整报告接口。
- 面试草稿已支持 Redis 和本地回退，但未配置 Redis 的多进程部署无法共享本地草稿。
- Vite 构建包受 Element Plus/ECharts 影响超过 500kB，后续拆路由时一并处理 code splitting。

### 4.4 前台体验要求

- 所有按钮都有 loading/disabled 状态。
- 所有 AI 生成步骤都要显示进度，不让用户误以为卡死。
- SSE 断线后允许重试，不重复写入追问。
- 回答草稿自动保存，刷新页面不丢。
- 移动端至少保证可查看邀请、上传简历、完成文本面试。
- 报告对候选人和 HR 分权限展示，候选人不一定能看到完整内部评分。

## 5. 后台功能完善方案

后台指 HR/面试官/Admin 控制台。当前已有基础看板和会话列表，但还缺真实招聘业务管理。

### 5.1 后台信息架构

建议后台导航：

    总览 Dashboard
    岗位管理 Jobs
    候选人 Candidates
    面试批次 Batches
    面试会话 Interviews
    题库/知识库 Knowledge
    评分标准 Rubrics
    报告中心 Reports
    用户与权限 Users & Roles
    系统监控 Operations

### 5.2 后台关键页面

| 页面 | 企业级功能 |
| --- | --- |
| Dashboard | 面试完成率、平均分、通过率、风险候选人、队列状态、LLM 成本 |
| 岗位管理 | JD、技能标签、级别、题目策略、评分权重 |
| 候选人管理 | 候选人列表、简历版本、来源、标签、阶段状态 |
| 面试批次 | 批量邀请、有效期、完成进度、异常重试 |
| 面试会话 | 会话详情、题目回答、追问 trace、AI 报告、人工复核 |
| 题库管理 | 题目 CRUD、难度、技能标签、版本发布 |
| 知识库管理 | JD/题库/标准文档上传、向量化状态、引用检查 |
| 报告中心 | 筛选、导出、人工备注、推荐结论 |
| 系统监控 | API 延迟、任务队列、LLM 错误、Redis/PostgreSQL 状态 |

### 5.3 后台前端需要配合的工程改造

当前 App.vue 承担了较多全局状态。后台复杂后建议拆分：

    frontend/src/
      router/
        index.js
      stores/
        auth.js
        session.js
        candidate.js
        job.js
        task.js
      layouts/
        CandidateLayout.vue
        AdminLayout.vue
      views/
        candidate/
        admin/
      components/
        common/
        charts/
        interview/

建议引入：

- Vue Router：区分候选人前台和 HR 后台路由。
- Pinia：管理 token、用户、会话、任务状态。
- API client 拦截器：统一处理 401、403、请求错误、trace id。
- 设计 tokens：颜色、间距、字号、阴影、状态色统一。
- 权限路由：根据角色控制菜单和按钮。
- 可复用状态组件：Empty、Error、Loading、Retry、PermissionDenied。

#### 当前前端检查结论

| 当前文件/组件 | 现状 | 企业级风险 | 改造建议 |
| --- | --- | --- | --- |
| frontend/src/App.vue | 已缩减为 `RouterView` 容器，入口逻辑下沉到 `views/` 和 Pinia stores | 布局仍未进一步拆成 candidate/console layout 包，后续页面多时仍会膨胀 | 继续把岗位、候选人、批次、报告中心拆成独立路由页面 |
| CandidateInterviewRoom.vue | 已有候选人面试室、计时、逐题回答、EventSource 追问 | 缺断线续面、草稿持久化、面试状态锁定 | 增加草稿 API、重连策略、提交后只读态 |
| DashboardPanel.vue | 已有真实会话聚合和 ECharts 图表 | 指标偏少，不能支撑 HR 管理决策 | 增加岗位维度、批次维度、通过率、异常任务、LLM 成本 |
| SessionsPanel.vue | 已能查看历史会话 | 缺筛选、分页、批次、候选人、人工复核入口 | 后端补分页筛选 API，前端补高级筛选和复核动作 |
| api/client.js | 封装了 token 和请求错误 | 缺统一 401/403、trace id、重试、上传进度、任务轮询 | 引入 request client 层，支持拦截器和任务状态订阅 |
| style.css | 已有大量页面样式 | 后续页面增多后容易形成样式债 | 抽 tokens、layout、components 三层样式，固定状态色和间距规范 |

前端配合后端升级时，优先不要一次性重写 UI。推荐顺序是：

1. Vue Router 已引入，`/candidate` 和 `/console` 两套入口已拆清楚。
2. Pinia 已引入，`auth/session/task` 已先落地；`job/candidate/batch` store 等待后台页面扩展时补齐。
3. 然后补候选人邀请流和 HR 岗位/候选人/批次页面。
4. 题目生成、追问生成和评分任务状态已先接入前端；后续继续统一通知等任务体验。

### 5.4 前后台角色边界

| 功能 | 候选人端 | HR/面试官后台 |
| --- | --- | --- |
| 简历上传 | 可以上传自己的简历 | 可以上传/替换候选人简历 |
| 面试题 | 只看到当前面试题 | 可查看题目来源、命中知识库、难度 |
| 追问 | 看到 AI 追问 | 看到 trace、原因、人工追问入口 |
| 报告 | 看到候选人版反馈 | 看到完整评分、风险、录用建议 |
| 历史记录 | 只看自己的面试 | 按岗位/批次/候选人筛选 |
| 权限管理 | 无 | 用户、角色、组织、审计 |

## 6. 本机部署与配置建议

你的主机已有 PostgreSQL、Redis、MQ、Docker Desktop、Clash Verge，代理端口是 7897。建议本地开发分两种模式。

### 6.1 本机服务模式

适合开发调试，使用主机已有服务：

    $env:DATABASE_URL="postgresql+psycopg://interviewer_user:interviewer_password@127.0.0.1:5432/interviewer_db"
    $env:REDIS_URL="redis://127.0.0.1:6379/0"
    $env:INTERVIEW_TASK_QUEUE_BACKEND="redis"
    $env:INTERVIEW_TASK_QUEUE_NAME="queue:interview_tasks"
    $env:HTTP_PROXY="http://127.0.0.1:7897"
    $env:HTTPS_PROXY="http://127.0.0.1:7897"
    $env:LLM_PROVIDER="qwen"
    $env:DASHSCOPE_API_KEY="<your-key>"
    python -m alembic upgrade head
    uvicorn app.main:app --reload --port 8100
    python -m app.workers.interview_worker

### 6.2 Docker Compose 模式

适合模拟部署环境：

    app
    worker
    postgres
    redis
    prometheus
    grafana

Compose 需要新增：

- redis 服务和 healthcheck。（已完成）
- worker 服务，复用 app 镜像，启动 Redis 队列 worker。（已完成第一批）
- rabbitmq 服务和管理端口可作为后续替换 Redis 队列的增强项。
- prometheus 和 grafana 可作为后续阶段。
- app 环境变量注入 HTTP_PROXY/HTTPS_PROXY。
- 容器内访问宿主机 Clash Verge 代理，通常用 host.docker.internal:7897。

容器内代理建议：

    HTTP_PROXY=http://host.docker.internal:7897
    HTTPS_PROXY=http://host.docker.internal:7897
    NO_PROXY=localhost,127.0.0.1,postgres,redis

## 7. 推荐实施优先级

### P0：先把系统变成真实可用

1. 补岗位、候选人、邀请、评分标准模型。
2. 前端拆出候选人端和后台端路由。（已完成第一批）
3. Redis 接入：限流、短 token、草稿保存。
4. PostgreSQL 作为默认开发数据库，不再依赖 SQLite。
5. 完善业务状态机：running/evaluating/ai_reported/reviewed/archived 已收口，历史 `questions_generated/follow_up_generated/evaluated` 通过迁移和兼容映射归一。

### P1：把 AI 链路变成稳定可控

1. LLM Gateway：多模型、代理、超时、重试、JSON 校验。（已完成 Qwen 第一批 Gateway，待多模型/成本/熔断）
2. MQ/Worker：题目生成、追问、报告评分异步化。（题目生成、追问和报告评分已完成 Redis 队列 + 独立 Worker 第一批，通知/失败重试仍待异步化）
3. RAG 服务：pgvector/Milvus、Rerank、引用来源。
4. Prompt 版本管理和评估集。
5. 成本和耗时统计。

### P2：把项目变成企业级可运维

1. Prometheus + Grafana。
2. OpenTelemetry 链路追踪。
3. 审计日志、数据脱敏、导出权限。
4. CI/CD：后端测试、前端 build、Docker build。
5. 备份恢复、灰度发布、回滚方案。

## 8. 业务逻辑合理性检查

企业级 AI 面试官系统必须避免“AI 自嗨”，业务逻辑应遵循：

    岗位标准先行
    -> 候选人证据输入
    -> AI 结构化提问
    -> 候选人回答留痕
    -> AI 初评
    -> 面试官复核
    -> HR 决策
    -> 数据沉淀反哺题库和评分标准

建议状态机：

| 状态 | 含义 | 允许操作 |
| --- | --- | --- |
| invited | 已邀请 | 候选人进入、过期取消 |
| profile_ready | 资料完成 | 开始面试 |
| running | 面试中 | 作答、追问、草稿保存 |
| submitted | 已提交 | 触发 AI 评分 |
| evaluating | 评分中 | 查看任务进度 |
| ai_reported | AI 报告完成 | 面试官复核 |
| reviewed | 人工复核完成 | HR 决策 |
| archived | 归档 | 只读查看 |

## 9. 验收标准

升级后的项目至少满足：

| 类别 | 验收标准 |
| --- | --- |
| 后端 | 所有核心接口有鉴权、权限隔离、错误码、测试覆盖 |
| 前台 | 候选人可通过邀请链接完整完成一次面试，刷新不中断 |
| 后台 | HR 可管理岗位、候选人、批次、会话、报告和题库 |
| AI | 题目/追问/报告支持异步任务、失败重试、fallback |
| RAG | 题目来源可追溯，支持知识库版本和引用 |
| 高可用 | app/worker 可水平扩展，Redis/MQ/PostgreSQL 有健康检查 |
| 观测 | 能看到 API 延迟、错误率、队列堆积、LLM 调用失败和成本 |
| 安全 | 简历和报告访问有审计，候选人 PII 有脱敏策略 |
| 部署 | Docker Compose 可一键启动完整本地环境 |

## 10. 下一步落地建议

最建议先做企业级最小闭环：

1. 新增岗位、候选人、邀请、评分标准四类模型和 API。
2. 前端引入 Vue Router，拆分候选人门户和 HR 后台。（已完成第一批）
3. 接入 Redis，先实现限流、短 token、草稿保存。
4. 接入 MQ/Worker，把题目生成、追问生成和评分报告异步化。（已接入 Redis 队列 + 独立 Worker，通知发送和失败重试仍待）
5. 把 Qwen 客户端抽成 LLM Gateway，并补代理配置说明。（已完成第一批）
6. 增加 PostgreSQL + Redis + MQ 的 ready 检查和测试。

这样改完后，项目就不只是 AI 面试 demo，而是具备企业级系统骨架的真实 AI 招聘/测评平台。
