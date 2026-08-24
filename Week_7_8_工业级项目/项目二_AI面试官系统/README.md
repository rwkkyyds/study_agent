# 项目二：AI 面试官系统

## 项目定位

这是第 7-8 周的第二个工业级项目，目标是构建一个可演示、可扩展的 AI 面试官系统：

- 候选人上传或粘贴简历
- 系统结合目标岗位生成结构化面试题
- 候选人按题作答
- 系统从技术匹配度、项目表达、问题分析、沟通结构等维度评分
- 输出面试报告、追问建议和学习改进方向

项目一侧重企业客服、RAG 和转人工工作台；项目二侧重招聘面试、简历理解、动态提问和评分报告。

## 当前阶段

阶段六已完成：Element Plus + ECharts 企业级 HR/面试官后台 + 真实历史面试 API + FastAPI /web 托管 + SSE 流式追问 + 短期 stream token，并保留可选通义千问增强。

当前推进阶段七 Docker 部署：新增 `Dockerfile`、`docker-compose.yml`、`.dockerignore` 和 Docker 运行说明。Docker 默认使用 `app + postgres + redis` 三个服务，前端构建产物仍由 FastAPI 在 `/web/` 托管。

阶段八已补充企业级高可用升级方案：围绕 PostgreSQL、Redis、MQ、Docker Desktop、Clash Verge 7897 代理环境，规划前台候选人端、后台 HR/面试官端、异步 AI 工作流、真实 RAG、LLM Gateway、监控告警和生产化验收标准；其中阶段二认证层已先接入 refresh token、logout 黑名单、登录失败限流、接口限流和审计日志，3.2 面试业务域已落地岗位/候选人/批次/邀请/评分标准/人工复核/通知日志，并已接通候选人邀请入口和 rubric 权重评分。

默认仍使用确定性规则工作流保证测试稳定；当显式设置 `LLM_PROVIDER=qwen` 且提供 `DASHSCOPE_API_KEY` 时，题目生成和追问会调用通义千问增强，失败时自动回落到本地规则链路。

1. 注册/登录获取 Bearer Token
2. 解析 text/markdown/PDF 简历并保存候选人画像
3. 按岗位、简历关键词和难度检索岗位题库
4. 使用简历文本或 `resume_profile_id` 生成混合题库的面试题
5. 对单题回答生成多轮追问并保存追问快照
6. 在 `/web/` 企业级 HR 后台中查看数据看板、历史会话和 SSE 追问事件
7. 提交回答并保存回答和评分报告

前端源码位于 `frontend/`，构建产物由 FastAPI 在 `/web/` 托管。后续阶段再逐步补面试话术沉淀、简历亮点包装和更完整的生产稳定性能力。

## 快速启动

PowerShell:

    cd "C:\Users\admin\Desktop\agent_study\Week_7_8_工业级项目\项目二_AI面试官系统"
    pip install -r requirements.txt
    # 可选：启用通义千问增强。不要把真实 Key 写入代码仓库。
    $env:LLM_PROVIDER="qwen"
    $env:DASHSCOPE_API_KEY="<your-dashscope-api-key>"
    $env:QWEN_MODEL="qwen-plus"
    cd frontend
    npm install
    npm run build
    cd ..
    python -m alembic upgrade head
    uvicorn app.main:app --reload --port 8100

访问：

- API 文档：http://localhost:8100/docs
- 浏览器面试页面：http://localhost:8100/web/
- 健康检查：http://localhost:8100/health
- 认证接口：`POST /auth/register`、`POST /auth/login`、`POST /auth/refresh`、`POST /auth/logout`、`GET /auth/me`
- 简历接口：`POST /resumes/parse`、`POST /resumes/upload`、`GET /resumes/{profile_id}`，需要 `Authorization: Bearer <token>`
- 题库接口：`POST /question-bank/search`，需要 `Authorization: Bearer <token>`
- 面试接口：`GET /interviews/sessions`、`GET /interviews/sessions/{session_id}`、`POST /interviews/questions`、`POST /interviews/follow-up`、`POST /interviews/evaluate`、`POST /interviews/evaluate/async`、`GET /interviews/tasks/{task_id}`，需要 `Authorization: Bearer <token>`；`POST /interviews/questions` 支持传入 `invite_token`，自动绑定岗位、候选人、批次和评分标准；候选人接口返回脱敏报告
- 面试草稿接口：`GET /interviews/sessions/{session_id}/drafts`、`PUT /interviews/sessions/{session_id}/drafts`、`DELETE /interviews/sessions/{session_id}/drafts/{question_id}`、`DELETE /interviews/sessions/{session_id}/drafts`
- 招聘业务域接口：`POST/GET /hiring/jobs`、`POST/GET /hiring/candidates`、`POST/GET /hiring/batches`、`POST/GET /hiring/invites`、`GET /hiring/invites/{invite_token}`、`POST/GET /hiring/rubrics`、`POST/GET /hiring/manual-reviews`、`GET /hiring/interview-sessions/{session_id}/report`、`GET /hiring/notification-logs`
- 候选人邀请入口：访问 `/web/?invite_token=<token>` 可查看邀请详情、登录候选人账号并启动绑定邀请的面试
- 流式追问：`POST /interviews/follow-up/stream-token` 需要登录，`GET /interviews/follow-up/stream?token=...` 返回 SSE
- Redis：配置 `REDIS_URL` 后，支持流式追问短 Token 服务端存储、JWT 黑名单、登录失败限流、高成本面试接口限流、24 小时面试草稿和异步任务状态；未配置时保持本地开发回退
- 可选 Qwen 增强：`LLM_PROVIDER=qwen` + `DASHSCOPE_API_KEY`，健康检查会在 `/health/ready` 返回 Qwen 配置状态

## Docker 启动

PowerShell:

    cd "C:\Users\admin\Desktop\agent_study\Week_7_8_工业级项目\项目二_AI面试官系统"
    docker compose up --build -d
    docker compose ps
    docker compose logs -f app

访问：

- 浏览器面试页面：http://localhost:8100/web/
- API 文档：http://localhost:8100/docs
- 健康检查：http://localhost:8100/health
- 就绪检查：http://localhost:8100/health/ready

停止但保留 PostgreSQL 和 Redis 数据：

    docker compose down

更多说明见 `DOCKER_RUN.md`。

## 学习文档

项目二文档参考项目一的阶段拆解方式组织：先给阶段 README，再按专题解释关键模块，方便边做项目边复盘。

- `docs/01-项目总览/README.md`：业务背景、核心闭环、技术关键词
- `docs/01-项目总览/实施路线图.md`：阶段目标和验收标准
- `docs/02-阶段一_项目骨架/README.md`：项目骨架与最小业务闭环总览
- `docs/02-阶段一_项目骨架/01-应用入口.md` 到 `06-请求流程.md`：阶段一关键模块专题
- `docs/03-阶段二_数据层与认证/README.md`：数据层与认证总览
- `docs/03-阶段二_数据层与认证/01-认证体系.md` 到 `06-阶段二请求流程.md`：阶段二关键模块专题
- `docs/04-阶段三_简历解析与岗位画像/README.md`：阶段三简历解析与岗位画像总览
- `docs/05-阶段四_LangGraph面试工作流/README.md`：阶段四图式面试工作流总览，详细标注 `.py` 路径
- `docs/06-阶段五_RAG与题库/README.md`：阶段五 RAG 与岗位题库总览，详细标注 `.py` 路径
- `docs/07-阶段六_前端与流式面试/README.md`：阶段六企业级 HR 后台、历史 API、SSE 接口、stream token 和测试验收
- `DOCKER_RUN.md`：阶段七 Docker 本地部署、Qwen 环境变量和数据持久化说明
- `docs/08-企业级高可用升级方案/README.md`：阶段八高可用企业级升级蓝图、前台/后台配合、Redis/MQ/代理配置和验收标准

## 运行测试

    cd frontend
    npm install
    npm run build
    cd ..
    python -m pytest -q

## 阶段路线

- 阶段一：项目骨架、业务流程、健康检查、mock 面试工作流
- 阶段二：用户与面试数据模型、JWT/Refresh Token 认证、logout 黑名单、登录限流、审计日志、SQLAlchemy 落库和 Alembic 迁移
- 阶段三：简历解析与岗位画像，支持 PDF/Markdown/Text
- 阶段四：LangGraph 面试工作流，支持题目生成、追问、评分
- 阶段五：RAG 接入，基于简历项目和岗位知识库生成针对性问题
- 阶段六：Element Plus + ECharts 企业级 HR 后台、真实历史面试 API、FastAPI 静态托管、短期 stream token、SSE 流式追问、可选通义千问增强
- 阶段七：Docker Compose、本地部署、PostgreSQL/Redis 持久化和容器就绪检查
- 阶段八：企业级高可用升级方案，已落地认证安全、Redis 基础设施、接口限流、3.2 招聘业务域模型/API、邀请启动面试绑定链路、rubric 权重评分、报告权限分层、Redis 面试草稿/断点续面和 3.4 异步评分任务状态基础能力，后续继续推进后台 HR/面试官端、MQ 异步化、真实 RAG、LLM Gateway、监控告警和可落地验收标准


