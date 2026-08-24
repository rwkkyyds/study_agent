# 项目进度

## 2026-08-17

### 阶段一：完成

- 完成 FastAPI 项目骨架
- 完成健康检查接口
- 完成确定性面试题生成和评分报告工作流
- 完成基础测试

### 阶段二：完成

- 完成用户、面试会话、题目、回答、报告 SQLAlchemy 模型
- 完成 JWT 注册、登录、当前用户和管理员用户管理接口
- `/interviews/questions` 接入 JWT，并保存会话和题目快照
- `/interviews/evaluate` 接入 JWT，会话按用户隔离，并保存回答和评分报告
- 新增 Alembic 初始迁移 `202608170001_initial_auth_interviews.py`
- 新增认证和面试持久化测试
- 验证 `python -m pytest -q` 通过


### 阶段二：企业级认证权限补强

- 按阶段八方案补齐 access token + refresh token 生命周期，新增 `/auth/refresh` 和 `/auth/logout`
- 新增 JWT 黑名单和登录失败限流，Redis 配置时走 Redis，未配置时保留本地测试回退
- 新增 `organizations`、`roles`、`permissions`、`user_roles`、`role_permissions`、`audit_logs` 作为 RBAC 和审计底座
- 新增 `app/services/audit.py`，注册、登录、刷新、退出、管理员创建用户写入审计日志
- 新增 Alembic 迁移 `202608230001_enterprise_auth_phase_two.py`
- 新增 refresh 轮换、logout 黑名单、登录限流和审计测试
- 验证 `python -m pytest -q` 通过：49 passed
### 阶段三：完成

- 新增 `/resumes/parse`，支持 text/markdown 简历正文解析
- 新增 `/resumes/upload`，支持 text/markdown/PDF 文件上传解析
- 新增 `/resumes/{profile_id}`，支持当前用户读取自己的候选人画像
- 新增候选人画像模型 `ResumeProfile`，保存原文、标准化文本、技能栈、项目、年限和岗位关键词
- `/interviews/questions` 支持通过 `resume_profile_id` 复用已解析画像
- 面试会话保存关联的 `resume_profile_id`
- 新增 Alembic 阶段三迁移 `202608180001_add_resume_profiles.py`
- 新增阶段三解析、上传、用户隔离和画像驱动面试测试
- 验证 `python -m pytest -q` 通过

### 阶段四：完成

- 新增 `app/workflow/interview_graph.py`，实现图式 LangGraph 风格面试工作流
- 保留 `app/workflow/interview.py` 作为兼容入口，继续导出 `InterviewWorkflow`
- 题目生成拆为 `resume_parse_node`、`job_profile_node`、`question_generation_node`
- 评分报告拆为 `answer_analysis_node`、`follow_up_node`、`scoring_node`、`report_node`
- 新增 `/interviews/follow-up`，根据单题回答生成多轮追问
- 新增 `InterviewFollowUp` ORM 模型，保存追问快照、原因和 workflow trace
- 新增 Alembic 阶段四迁移 `202608190001_add_interview_follow_ups.py`
- 新增 `tests/test_interview_graph_workflow.py`，覆盖 trace、追问持久化和越权路径
- 新增 `docs/05-阶段四_LangGraph面试工作流/`，按 `.py` 路径详细解释阶段四实现
- 当前沙箱无法运行 pytest 环境，已使用内置 Python 对 `app/`、`tests/`、`alembic/` 完成语法编译检查

### 阶段五：完成

- 新增 `app/knowledge/question_bank.py`，提供本地结构化岗位题库
- 新增 `app/schemas/question_bank.py`，定义题库检索请求与响应
- 新增 `app/services/question_bank.py`，实现关键词抽取、确定性打分排序和题目转换
- 新增 `app/api/question_bank.py`，提供 `/question-bank/search` 检索接口
- `app/main.py` 注册 `question_bank_router`
- `app/workflow/interview_graph.py` 新增 `rag_retrieval_node`
- `/interviews/questions` 混入岗位题库检索题，并在 `workflow_trace` 中显示 RAG 检索节点
- 新增 `tests/test_question_bank.py`，覆盖认证、检索排序、题目转换和工作流混入
- 新增 `docs/06-阶段五_RAG与题库/`，详细解释题库、检索服务、工作流接入和测试
- 验证 `python -m pytest -q` 通过：21 passed, 1 warning
- 验证 Alembic 临时 SQLite 迁移烟测通过

### 阶段六：完成

- 新增 `POST /interviews/follow-up/stream-token`，用 Bearer JWT 换取短期 SSE stream token
- 新增 `GET /interviews/follow-up/stream?token=...`，返回 `text/event-stream`
- `app/services/auth.py` 支持追问 stream token 创建、用途校验和过期校验
- `app/services/interviews.py` 新增公开会话归属校验方法，API 层不再调用私有方法
- 新增 `frontend/` Vue 3 + Vite 前端工程
- `frontend/vite.config.js` 构建输出到 `app/web`，由 `app/main.py` 继续挂载 `/web` 静态页面
- Vue 页面升级为 Element Plus + ECharts 企业级 HR/面试官后台，支持数据看板、历史会话、创建面试、SSE 追问和评分报告图表
- 新增 `tests/test_interview_streaming.py`，覆盖认证、越权、SSE 事件、追问落库和 token 异常
- 新增 `tests/test_interview_sessions_api.py`，覆盖历史会话列表、详情聚合、用户隔离和无报告状态
- 更新 `tests/test_web_assets.py`，从 `/web/` 解析 Vite JS/CSS asset 并验证企业后台资源可访问
- 更新 `docs/07-阶段六_前端与流式面试/`，详细解释企业级 HR 后台、历史 API、SSE 设计、浏览器流程和测试验收
- 阶段六企业级后台不新增数据库表，不新增 Alembic 迁移
- 验证 `python -m pytest -q` 通过：41 passed, 1 warning
- 企业级优化：新增可选 `LLM_PROVIDER=qwen` + `DASHSCOPE_API_KEY` 通义千问增强，不把密钥写入代码
- 新增 `app/services/qwen_llm.py`，通过 DashScope OpenAI 兼容接口生成增强题目和追问
- `app/workflow/interview_graph.py` 在 Qwen 成功时记录 `qwen_*_enrichment_node`，失败时记录 `qwen_*_enrichment_skipped` 并回落到确定性链路
- `/health/ready` 返回 Qwen 配置状态，便于部署前确认 LLM 依赖
- 新增 `tests/test_qwen_llm.py`，覆盖 Qwen JSON 解析、工作流增强和失败降级
- 验证 `python -m pytest -q` 通过：41 passed, 1 warning

### 阶段七：Docker 部署推进

- 新增生产前最小后端硬化：默认 CORS 改为本地白名单、生产环境禁止默认 JWT 密钥、简历上传默认限制 5MB
- `/health/ready` 新增数据库 `SELECT 1` 检查，数据库不可用时返回 503；Qwen 继续作为可选依赖展示配置状态
- `requirements.txt` 新增 `psycopg[binary]`，支持 Docker 默认 PostgreSQL 连接
- 新增多阶段 `Dockerfile`：先构建 Vue 前端，再安装 Python 依赖，最终镜像执行 `alembic upgrade head` 和 `uvicorn`
- 新增 `docker-compose.yml`：包含 `app`、`postgres` 与 `redis` 三个服务，宿主机映射 `8100:8000`，PostgreSQL 和 Redis 仅 Docker 内网访问并使用 volume 持久化
- 新增 `.dockerignore` 和 `DOCKER_RUN.md`，运行说明只包含占位符，不写入真实通义千问 Key
- 新增配置、健康检查和上传大小限制测试

### 阶段八：企业级基础设施第一批落地

- 新增 Redis 配置项与客户端封装，未配置 `REDIS_URL` 时保持本地开发和测试回退
- `/health/ready` 纳入 Redis 就绪检查：未配置显示 disabled，已配置但不可用返回 503
- 流式追问 Token 在 Redis 模式下改为 opaque id，候选人回答只存服务端短期 TTL 数据并一次性消费
- `docker-compose.yml` 接入 `redis:7-alpine` 服务、healthcheck、volume 和 app 依赖
- 新增 Redis Token 隐私/一次性消费测试和 Redis ready 失败测试
- 验证 `python -m pytest -q` 通过：49 passed

### 阶段八：3.2 面试业务域建模启动

- 完善部分完成项：新增多角色权限依赖 `require_any_role`，支持 HR/Admin/Interviewer 按业务域访问后台能力
- 新增通用 API 限流服务，Redis 配置时使用 `rate:{user_id}:{route}:{minute}`，未配置 Redis 时保留进程内回退
- 高成本面试接口 `/interviews/questions`、`/interviews/follow-up`、`/interviews/follow-up/stream-token`、`/interviews/evaluate` 接入接口限流
- 新增 `jobs`、`candidate_profiles`、`interview_batches`、`interview_invites`、`evaluation_rubrics`、`manual_reviews`、`notification_logs` 企业招聘业务域模型
- `interview_sessions` 新增可选业务外键：`job_id`、`candidate_profile_id`、`interview_batch_id`、`invite_id`、`rubric_id`，为候选人邀请流和人工复核流转预留关联
- 新增 `/hiring/*` API：岗位、候选人、批次、邀请、评分标准、人工复核、通知日志的最小可用后台接口
- 新增 Alembic 迁移 `202608230002_hiring_domain_models.py`
- 新增 `tests/test_hiring_domain.py`，覆盖 HR 业务域创建、候选人权限拒绝、公开邀请查询、人工复核和接口限流
- 验证 `python -m pytest -q` 通过：53 passed

### 阶段八：邀请启动面试链路打通

- `/hiring/invites/{invite_token}` 响应新增岗位名称、岗位级别、候选人姓名和脱敏邮箱，支撑候选人邀请落地页展示
- `/interviews/questions` 新增 `invite_token`、`job_id`、`candidate_profile_id`、`interview_batch_id`、`rubric_id` 可选入参
- 候选人通过 `invite_token` 启动面试时，系统自动带出岗位标题、候选人档案、招聘批次和该岗位最新启用评分标准
- 新生成的 `interview_sessions` 会写入 `job_id`、`candidate_profile_id`、`interview_batch_id`、`invite_id`、`rubric_id`
- 邀请启动后自动把邀请标记为 `accepted`，记录 `used_at`，并把未绑定用户的候选人档案绑定到当前 candidate 用户
- 防止重复消费邀请：同一邀请已创建会话后，再次生成题目返回 409
- 新增测试覆盖候选人邀请启动面试、会话外键绑定、邀请状态更新、候选人绑定和重复邀请拦截
- 验证 `python -m pytest -q` 通过：54 passed

### 阶段八：前台候选人邀请入口落地

- 新增 `frontend/src/components/CandidateInviteLanding.vue`，支持候选人通过 `/web/?invite_token=<token>` 进入邀请落地页
- 邀请落地页展示岗位名称、岗位级别、候选人姓名、脱敏邮箱、有效期和邀请状态
- 未登录候选人点击开始时进入登录页，登录后自动回到邀请页继续启动面试
- 已登录候选人可在邀请页填写简历/项目经历、选择难度和题数，并通过 `invite_token` 调用 `/interviews/questions`
- 保留原自由练习入口，候选人可从邀请模式切回普通 `CandidateSetup`
- 更新 Vite 构建产物 `app/web/`，FastAPI `/web/` 已能托管新邀请入口
- 更新 `tests/test_web_assets.py`，验证构建产物包含邀请入口和 `.candidate-invite` 样式
- 验证 `npm run build` 通过
- 验证 `python -m pytest -q` 通过：54 passed

### 阶段八：风险后续补充记录

- 前端仍是轻量单页状态管理，尚未引入 Vue Router/Pinia；页面继续增多时需要按 `/candidate` 与 `/console` 拆路由
- 邀请异常态目前有基础提示，后续需要补独立的过期页、已使用页等专门页面
- 评分标准已绑定到 `interview_sessions.rubric_id` 并补齐报告权重计算；候选人版/HR 版报告已完成基础权限分层
- 前端构建包因 Element Plus/ECharts 仍超过 500kB，后续需要路由拆包或手动 chunk

### 阶段八：Redis 面试草稿与断点续面基础能力

- 新增 `app/services/interview_drafts.py`，Redis 配置时使用 `draft:{session_id}:{question_id}` 保存草稿，TTL 默认 24 小时
- 未配置 Redis 时保留进程内草稿回退，方便本地开发和测试；企业部署仍建议始终配置 Redis
- 新增草稿接口：`GET /interviews/sessions/{session_id}/drafts`、`PUT /interviews/sessions/{session_id}/drafts`、`DELETE /interviews/sessions/{session_id}/drafts/{question_id}`、`DELETE /interviews/sessions/{session_id}/drafts`
- 所有草稿接口都会校验当前用户会话归属，并校验 `question_id` 属于该会话
- `/interviews/evaluate` 生成正式评分报告后自动清理该会话草稿，避免已提交答案和草稿状态冲突
- 候选人面试间 `CandidateInterviewRoom.vue` 新增草稿恢复、防抖自动保存和保存状态提示
- 邀请页 `CandidateInviteLanding.vue` 能识别已接受邀请对应的历史会话，并提供“继续上次面试”入口
- `docker-compose.yml` 新增 `INTERVIEW_DRAFT_TTL_SECONDS` 配置，默认 `86400`
- 更新 Vite 构建产物 `app/web/`，并清理旧 hash 静态文件
- 新增/更新测试覆盖草稿保存、恢复、删除、越权隔离、评分后清理和前端构建产物包含草稿能力
- 验证 `python -m pytest tests/test_interview_sessions_api.py tests/test_web_assets.py -q` 通过：8 passed

### 阶段八：Rubric 权重评分落地

- `InterviewWorkflow.evaluate_answers` 支持接收岗位评分标准维度和权重，未绑定 rubric 时保持原 35%/25%/25%/15% 默认评分逻辑
- `InterviewPersistenceService.evaluate_answers` 会读取会话绑定的 `evaluation_rubrics`，把 `dimensions` 与 `weights` 传入报告生成流程
- 报告维度会按 rubric 展示名称返回，并把中文岗位维度映射到底层 `technical`、`structure`、`project`、`risk` 四类确定性分数
- 已覆盖“绑定 rubric 后报告总分按权重变化、报告详情持久化同分数”的回归测试
- 验证 `python -m pytest tests/test_hiring_domain.py tests/test_interview_workflow.py tests/test_interview_graph_workflow.py tests/test_interview_sessions_api.py -q` 通过：22 passed
- 全量验证 `python -m pytest -q` 通过：56 passed；`docker compose config` 通过；`python -m alembic heads` 显示 `202608230002 (head)`
### 阶段八：报告权限分层与 3.4 异步评分任务启动

- 候选人侧 `/interviews/evaluate` 和 `/interviews/sessions/{session_id}` 返回 `visibility=candidate` 的脱敏报告，保留总分、等级、优势、追问和学习建议，隐藏内部维度分和风险标记
- 后台侧新增 `GET /hiring/interview-sessions/{session_id}/report`，仅 `interviewer/hr/admin` 可查看 `visibility=internal` 的完整评分维度和风险标记
- 新增 `app/services/interview_tasks.py`，任务状态使用 Redis `task:{task_id}`，未配置 Redis 时走本地进程回退
- 新增 `POST /interviews/evaluate/async` 和 `GET /interviews/tasks/{task_id}`，先以 FastAPI BackgroundTasks 作为本地过渡 Worker 执行 `interview.report` 评分任务
- `docker-compose.yml` 和运行说明新增 `INTERVIEW_TASK_TTL_SECONDS=86400`
- 新增/更新测试覆盖候选人报告脱敏、后台完整报告权限、异步评分任务轮询和任务用户隔离
- 验证 `python -m pytest tests/test_interview_workflow.py tests/test_interview_sessions_api.py tests/test_hiring_domain.py tests/test_interview_graph_workflow.py -q` 通过：23 passed
- 全量验证 `python -m pytest -q` 通过：57 passed；`docker compose config` 通过；`python -m alembic heads` 显示 `202608230002 (head)`

### 阶段八：P0 收尾与 P1 LLM Gateway 第一批落地

- 前端新增 Vue Router，入口拆为 `/web/candidate` 候选人门户和 `/web/console` HR/面试官后台，并保留 `/web/?invite_token=<token>` 旧入口兼容
- 前端新增 Pinia `auth/session/task` stores：token、会话详情、回答、SSE 事件、异步评分任务状态从 `App.vue` 下沉到 store
- HR 后台打开已评分会话时会调用 `GET /hiring/interview-sessions/{session_id}/report`，优先展示 `visibility=internal` 的完整维度分和风险标记
- 候选人面试室和后台工作台的“生成评分报告”改为调用 `/interviews/evaluate/async` 并轮询 `/interviews/tasks/{task_id}`，前端正式消费 3.4 异步评分任务能力
- 新增 `app/services/llm_gateway.py`，把 Qwen provider 的路由、HTTP_PROXY 环境代理继承、超时、重试、Prompt 版本标识和 JSON 对象校验集中到 LLM Gateway
- `app/services/qwen_llm.py` 改为通过 LLM Gateway 调用 DashScope OpenAI 兼容接口，保留原有失败回退工作流
- `/health/ready` 新增 `llm_gateway` 依赖状态，同时保留原 Qwen 配置状态，方便部署前检查 AI provider
- FastAPI 静态托管新增 `/web/candidate` 直达入口，Vite 代理新增 `/hiring`，构建产物已更新并清理旧 JS hash
- 新增/更新测试覆盖候选人入口托管、前端资产中的内部报告接口/异步任务接口、LLM Gateway JSON 校验和健康检查
- 验证 `npm run build` 通过；`python -m pytest tests/test_web_assets.py tests/test_llm_gateway.py tests/test_qwen_llm.py tests/test_health.py tests/test_interview_sessions_api.py tests/test_hiring_domain.py -q` 通过：26 passed
- 全量验证 `python -m pytest -q` 通过：61 passed；`docker compose config` 通过；`python -m alembic heads` 显示 `202608230002 (head)`
- 剩余风险：追问生成/通知发送仍未进入异步队列；业务状态机仍需从旧 `questions_generated/evaluated` 逐步统一；RAG 仍是本地关键词检索；Element Plus/ECharts 构建包仍超过 500kB，需要后续路由懒加载/manualChunks

### 阶段八：3.4 Redis 队列 Worker 第一批落地

- 新增配置 `INTERVIEW_TASK_QUEUE_BACKEND`、`INTERVIEW_TASK_QUEUE_NAME`、`INTERVIEW_WORKER_POLL_TIMEOUT_SECONDS`，默认本地 `background`，Docker Compose 使用 `redis`
- `POST /interviews/questions/async` 和 `POST /interviews/evaluate/async` 在 Redis 队列模式下分别把 `interview.questions`、`interview.report` 任务投递到 `queue:interview_tasks`，未启用 Redis 队列时继续使用 FastAPI BackgroundTasks 回退
- 新增 `app/services/interview_task_runner.py`，API 回退任务和独立 Worker 共用同一套评分执行逻辑，避免异步路径分叉
- 新增 `app/workers/interview_worker.py`，支持 `python -m app.workers.interview_worker` 持续消费 Redis 队列并更新 `task:{task_id}` 状态
- Docker Compose 新增 `worker` 服务，复用 app 镜像，依赖 app/postgres/redis 健康状态后启动，并加入 Redis ping healthcheck
- `/health/ready` 新增 `interview_worker_queue` 依赖状态：本地未启用时显示 `inline_fallback`，Docker Redis 队列模式显示 `enabled`
- 新增测试覆盖题目生成/评分任务的 Redis 队列投递、独立 worker `run_once` 消费、任务状态从 `queued` 到 `succeeded`、候选人报告脱敏结果保持不变
- 验证 `python -m pytest tests/test_interview_sessions_api.py tests/test_health.py -q` 通过：11 passed；`python -m pytest tests/test_web_assets.py tests/test_llm_gateway.py tests/test_qwen_llm.py -q` 通过：10 passed
- 全量验证 `python -m pytest -q` 通过：62 passed；`docker compose config` 通过并包含 `worker` 服务；`python -m alembic heads` 显示 `202608230002 (head)`

### 阶段八：P0 状态机收尾与 P1 追问异步化落地

- 新增 `app/services/interview_status.py`，集中定义阶段八面试状态机，并兼容映射历史 `questions_generated/follow_up_generated/evaluated`
- 新增 Alembic 迁移 `202608250001_normalize_interview_session_statuses.py`，把历史会话状态迁移为 `running` / `ai_reported`
- 同步面试服务状态流转：题目生成和追问保持 `running`，评分入队标记 `evaluating`，评分完成标记 `ai_reported`
- 3.4 异步任务补齐 `interview.follow_up`：新增 `/interviews/follow-up/async`，BackgroundTasks 回退和 Redis 独立 worker 共用 `run_generate_follow_up_task`
- 前端 `taskStore` 新增追问异步任务创建/轮询，HR 工作台默认使用异步追问，并保留 SSE 预览入口
- README、Docker 说明和企业级升级方案同步更新：队列范围扩展为 `interview.questions` / `interview.follow_up` / `interview.report`
- 新增/更新测试覆盖 P0 状态机、追问异步 BackgroundTasks、追问 Redis worker、前端构建资产中的 `/interviews/follow-up/async`
- 验证 `python -m pytest tests/test_interview_sessions_api.py tests/test_interview_workflow.py tests/test_interview_graph_workflow.py tests/test_interview_streaming.py -q` 通过：30 passed；`python -m pytest tests/test_web_assets.py -q` 通过：4 passed
- 全量验证 `python -m pytest -q` 通过：66 passed；`docker compose config` 通过；`python -m alembic heads` 显示 `202608250001 (head)`；`npm run build` 通过，仍保留 Vite 大 chunk 警告
- 剩余风险：通知发送、失败重试/死信、多模型成本统计、真实 RAG/Rerank、Prompt 评估集和生产观测仍待后续 P1/P2 阶段补齐；Element Plus/ECharts bundle 仍超过 500kB，需要后续拆包
