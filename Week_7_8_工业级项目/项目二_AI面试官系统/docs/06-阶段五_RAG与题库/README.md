# 阶段五：RAG 与岗位题库

> 阶段五把“题目生成”从纯规则生成升级为“岗位画像 + 简历关键词 + 本地题库检索”的 RAG 风格链路。

## 阶段定位

阶段四已经把面试流程拆成图式节点：简历解析、岗位画像、题目生成、回答分析、追问、评分、报告。

阶段五继续增强题目生成节点之前的上下文来源：系统不再只依赖简历弱信号和固定模板，而是先从岗位题库中检索与岗位、简历、难度匹配的问题，再混入最终面试题列表。

当前阶段没有接真实向量数据库，而是用结构化本地题库模拟 RAG 检索。这样可以先把数据结构、检索服务、API、工作流节点和测试打通，后续再把检索实现替换为 Milvus、pgvector 或其他向量库。

## 阶段目标

- 建立本地岗位题库 `app/knowledge/question_bank.py`
- 新增题库检索 schema `app/schemas/question_bank.py`
- 新增题库检索服务 `app/services/question_bank.py`
- 新增题库检索接口 `app/api/question_bank.py`
- 在应用入口 `app/main.py` 注册 `/question-bank/search`
- 在图式工作流 `app/workflow/interview_graph.py` 中新增 `rag_retrieval_node`
- 题目生成混入题库检索问题，并保留原有简历信号问题
- 支持按岗位、简历关键词、难度进行确定性排序
- 新增 `tests/test_question_bank.py` 覆盖题库 API、检索器和面试题混合链路

## 涉及文件

| 文件路径 | 作用 |
|----------|------|
| `app/knowledge/question_bank.py` | 本地岗位题库，模拟后续向量库中的知识库数据 |
| `app/services/question_bank.py` | 题库检索器，负责关键词抽取、打分排序、转成面试题 |
| `app/schemas/question_bank.py` | `/question-bank/search` 的请求和响应模型 |
| `app/api/question_bank.py` | 题库检索 API 路由 |
| `app/main.py` | 注册 `question_bank_router` |
| `app/workflow/interview_graph.py` | 新增 `rag_retrieval_node`，并把检索题混入题目生成 |
| `tests/test_question_bank.py` | 阶段五测试文件 |
| `docs/06-阶段五_RAG与题库/` | 阶段五学习文档 |

## 新增接口

| 接口 | 用途 | 是否登录 |
|------|------|----------|
| `POST /question-bank/search` | 按岗位、简历关键词和难度检索题库 | 是 |

请求核心字段：

- `job_title`：目标岗位
- `resume_text`：简历或画像文本，可选
- `difficulty`：题目难度
- `top_k`：返回题目数量

响应核心字段：

- `query_keywords`：本次检索抽取出的关键词
- `items`：按相关性排序后的题库题目
- `score`：本地确定性检索分数

## 工作流变化

阶段四题目生成链路：

```text
resume_parse_node -> job_profile_node -> question_generation_node
```

阶段五题目生成链路：

```text
resume_parse_node -> job_profile_node -> rag_retrieval_node -> question_generation_node
```

`rag_retrieval_node` 会调用 `QuestionBankRetriever`，从岗位题库中找出和岗位、简历、难度最相关的题目，然后交给 `question_generation_node` 混入最终面试题列表。

## 完成标准

- `/question-bank/search` 需要登录后访问
- 题库检索能返回 query keywords 和排序后的题目
- 检索器能把题库条目转换成 `InterviewQuestion`
- `/interviews/questions` 的 `workflow_trace` 包含 `rag_retrieval_node`
- `/interviews/questions` 返回的问题中包含题库来源题目
- 原有认证、简历解析、追问、评分测试继续通过
- `python -m pytest -q` 通过

## 文档索引

| 文档 | 内容 |
|------|------|
| [01-岗位题库设计](01-岗位题库设计.md) | 本地题库字段、难度分层、为什么先不用真实向量库 |
| [02-检索服务](02-检索服务.md) | `QuestionBankRetriever` 如何抽关键词、打分、排序 |
| [03-工作流接入](03-工作流接入.md) | `rag_retrieval_node` 如何进入图式工作流 |
| [04-接口与测试](04-接口与测试.md) | `/question-bank/search` 和阶段五测试说明 |
