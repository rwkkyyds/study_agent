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
