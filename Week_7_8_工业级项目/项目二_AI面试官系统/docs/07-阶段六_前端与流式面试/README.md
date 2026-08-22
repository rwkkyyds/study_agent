# 阶段六：企业级 HR 后台与流式面试

> 阶段六把阶段二到五完成的认证、面试会话、题目生成、追问和评分报告串成企业级 HR/面试官后台。本次补全重点是：Vue 3 + Vite 前端升级为 Element Plus + ECharts 工作台，并新增真实历史面试 API。可选 Qwen 增强继续保留，默认仍走本地确定性链路。

## 阶段定位

阶段五之前，项目已经具备后端核心闭环：

- 用户可以注册、登录并拿到 JWT
- 简历和岗位可以生成面试题
- 单题回答可以生成追问并落库
- 多题回答可以生成评分报告
- 题库检索可以影响题目生成
- SSE 追问接口可以按 `trace`、`follow_up`、`done` 输出事件

阶段六不再停留在 demo 页面，而是把浏览器入口升级成面试运营后台。HR 或技术面试官可以在一个工作台内查看数据看板、创建面试、打开历史会话、发起实时追问和查看报告图表。

## 阶段目标

- 使用 `Element Plus` 建立企业 SaaS 风格后台界面
- 使用 `ECharts` 展示状态分布、评分趋势和评分维度图表
- 新增 `GET /interviews/sessions` 历史会话列表接口
- 新增 `GET /interviews/sessions/{session_id}` 会话详情接口
- 继续复用已有会话、题目、回答、追问和报告表，不新增迁移
- 页面支持登录、数据看板、会话表格、创建面试、实时追问、评分报告
- 保留 `app/main.py` 对 `/web` 的静态挂载
- 保留 stream token + EventSource 的 SSE 认证方案
- 更新测试，覆盖历史 API、用户隔离、Vite 静态资源和现有 SSE 回归

## 关键文件

| 文件路径 | 作用 |
|----------|------|
| `app/api/interviews.py` | 新增历史会话列表和详情接口，保留题目、追问、评分接口 |
| `app/services/interviews.py` | 聚合当前用户会话、题目、回答、追问和报告 |
| `app/schemas/interview.py` | 定义会话摘要、会话列表和会话详情响应模型 |
| `frontend/package.json` | 新增 Element Plus、图标库、ECharts 和 vue-echarts |
| `frontend/src/App.vue` | 企业后台 AppShell：侧边栏、顶部栏、主内容区和全局状态 |
| `frontend/src/components/DashboardPanel.vue` | 面试数、平均分、追问数和图表看板 |
| `frontend/src/components/InterviewCreatePanel.vue` | 岗位、难度、题数、简历输入和题目生成 |
| `frontend/src/components/SessionsPanel.vue` | 真实历史会话表格和详情入口 |
| `frontend/src/components/InterviewWorkspace.vue` | 题目队列、回答区和 SSE 事件流 |
| `frontend/src/components/ReportPanel.vue` | 评分图表、优势、风险和学习建议 |
| `tests/test_interview_sessions_api.py` | 历史 API、详情聚合和用户隔离测试 |
| `tests/test_web_assets.py` | Vite 构建产物和企业后台资源测试 |

## 新增接口

| 接口 | 用途 | 认证 |
|------|------|------|
| `GET /interviews/sessions` | 当前用户历史面试列表 | Bearer JWT |
| `GET /interviews/sessions/{session_id}` | 当前用户某次面试详情 | Bearer JWT |
| `POST /interviews/follow-up/stream-token` | 换取短期 SSE token | Bearer JWT |
| `GET /interviews/follow-up/stream?token=...` | 打开追问 SSE 流 | 短期 query token |
| `GET /web/` | 企业级面试管理工作台 | 无 |

## 页面链路

1. 用户访问 `/web/`，进入企业级 HR/面试官后台
2. 登录后前端保存 JWT，并拉取 `/interviews/sessions`
3. 数据看板基于真实会话聚合面试数、已评分数、平均分和追问次数
4. 创建面试调用 `/interviews/questions`，生成题目后进入工作台
5. 会话列表可以打开历史详情，详情来自 `/interviews/sessions/{session_id}`
6. 工作台内选择题目、保存回答、用 stream token 打开 SSE 追问
7. 提交评分后调用 `/interviews/evaluate`，报告区域展示图表和建议

## 完成标准

- `/web/` 展示企业级 HR/面试官后台，不再是 demo 双栏页
- `npm run build` 输出 `app/web/index.html` 和 `app/web/assets/*`
- 历史列表和详情接口只返回当前用户数据
- 无报告会话的 `overall_score` 和 `level` 为 `null`，页面正常展示待评分状态
- SSE 追问、追问落库和会话状态更新不回退
- Element Plus 表单、表格、标签、步骤、加载态和空状态可用
- ECharts 看板和报告维度图可用
- 不新增数据库表，不新增 Alembic 迁移
- `python -m pytest -q` 通过

## 文档索引

| 文档 | 内容 |
|------|------|
| [01-SSE接口设计](01-SSE接口设计.md) | stream token、SSE 事件、认证边界和后端文件路径 |
| [02-前端页面结构](02-前端页面结构.md) | 企业级 Vue 后台结构、组件分工和构建产物关系 |
| [03-浏览器面试流程](03-浏览器面试流程.md) | 从登录到看板、历史会话、实时追问和报告的操作链路 |
| [04-测试与验收](04-测试与验收.md) | 历史 API、前端构建、静态资源、SSE 回归和全量测试 |
