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
- 新增 `docker-compose.yml`：包含 `app` 与 `postgres` 两个服务，宿主机映射 `8100:8000`，PostgreSQL 仅 Docker 内网访问并使用 volume 持久化
- 新增 `.dockerignore`、`.env.example` 和 `DOCKER_RUN.md`，环境模板只包含占位符，不写入真实通义千问 Key
- 新增配置、健康检查和上传大小限制测试


