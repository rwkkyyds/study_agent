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

阶段五已完成：本地岗位题库 + RAG 风格检索 + 题库驱动面试题生成。

当前仍使用确定性规则工作流保证测试稳定，业务链路已跑通：

1. 注册/登录获取 Bearer Token
2. 解析 text/markdown/PDF 简历并保存候选人画像
3. 按岗位、简历关键词和难度检索岗位题库
4. 使用简历文本或 `resume_profile_id` 生成混合题库的面试题
5. 对单题回答生成多轮追问并保存追问快照
5. 提交回答并保存回答和评分报告

后续阶段再逐步替换为 LangGraph、RAG、LLM、PostgreSQL、Redis、前端与 Docker 部署。

## 快速启动

PowerShell:

    cd "C:\Users\admin\Desktop\agent_study\Week_7_8_工业级项目\项目二_AI面试官系统"
    pip install -r requirements.txt
    python -m alembic upgrade head
    uvicorn app.main:app --reload --port 8100

访问：

- API 文档：http://localhost:8100/docs
- 健康检查：http://localhost:8100/health
- 认证接口：`POST /auth/register`、`POST /auth/login`、`GET /auth/me`
- 简历接口：`POST /resumes/parse`、`POST /resumes/upload`、`GET /resumes/{profile_id}`，需要 `Authorization: Bearer <token>`
- 题库接口：`POST /question-bank/search`，需要 `Authorization: Bearer <token>`
- 面试接口：`POST /interviews/questions`、`POST /interviews/follow-up`、`POST /interviews/evaluate`，需要 `Authorization: Bearer <token>`


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

## 运行测试

    python -m pytest -q

## 阶段路线

- 阶段一：项目骨架、业务流程、健康检查、mock 面试工作流
- 阶段二：用户与面试数据模型、JWT 认证、SQLAlchemy 落库、Alembic 初始迁移
- 阶段三：简历解析与岗位画像，支持 PDF/Markdown/Text
- 阶段四：LangGraph 面试工作流，支持题目生成、追问、评分
- 阶段五：RAG 接入，基于简历项目和岗位知识库生成针对性问题
- 阶段六：前端面试体验、SSE 流式输出
- 阶段七：Docker Compose、本地部署、面试报告与简历亮点沉淀





