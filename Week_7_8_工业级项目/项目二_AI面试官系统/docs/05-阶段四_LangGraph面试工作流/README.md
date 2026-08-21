# 阶段四：LangGraph 面试工作流

> 阶段四把原来的确定性单函数工作流，改造成“图式节点工作流”：简历解析节点、岗位画像节点、题目生成节点、回答分析节点、追问节点、评分节点、报告节点。

## 阶段定位

阶段一解决接口闭环，阶段二解决认证和落库，阶段三解决简历解析和候选人画像。

阶段四开始进入 AI 面试官系统的核心工作流编排：一次面试不再只是“调用一个函数生成题目或报告”，而是拆成多个可观察、可测试、可替换的节点。

当前实现使用本地图式工作流模拟 LangGraph 的 StateGraph 思路，没有强依赖外部 LLM，也没有要求真实 LangGraph 包必须安装。这样可以保证测试稳定，同时把未来迁移到真实 LangGraph 的接口形状和节点边界先固定下来。

## 阶段目标

- 新增图式工作流实现文件 `app/workflow/interview_graph.py`
- 保留兼容入口 `app/workflow/interview.py`
- 将题目生成拆成：简历解析节点 -> 岗位画像节点 -> 题目生成节点
- 将评分报告拆成：回答分析节点 -> 追问节点 -> 评分节点 -> 报告节点
- 新增多轮追问接口 `POST /interviews/follow-up`
- 新增追问快照表 `interview_follow_ups`
- 追问接口按当前用户校验面试会话归属
- 响应中返回 `workflow_trace`，方便学习和调试节点执行顺序
- 新增阶段四迁移和测试

## 涉及文件

| 文件路径 | 作用 |
|----------|------|
| `app/workflow/interview_graph.py` | 阶段四核心图式工作流，包含状态对象和各节点实现 |
| `app/workflow/interview.py` | 兼容入口，继续导出 `InterviewWorkflow`，避免 service 层大改 |
| `app/schemas/interview.py` | 新增追问请求/响应模型，并给题目/报告响应增加 `workflow_trace` |
| `app/api/interviews.py` | 新增 `/interviews/follow-up` 路由 |
| `app/services/interviews.py` | 新增 `generate_follow_up` 持久化服务方法 |
| `app/models/interview.py` | 新增 `InterviewFollowUp` ORM 模型和会话关系 |
| `app/models/__init__.py` | 导出 `InterviewFollowUp` |
| `alembic/env.py` | 迁移环境加载 `InterviewFollowUp` 模型 |
| `alembic/versions/202608190001_add_interview_follow_ups.py` | 阶段四数据库迁移 |
| `tests/test_interview_graph_workflow.py` | 阶段四图式工作流、追问、越权和 trace 测试 |

## 新增接口

| 接口 | 用途 | 是否登录 |
|------|------|----------|
| `POST /interviews/follow-up` | 根据某道题的回答生成追问 | 是 |

请求语义：

- `session_id`：当前面试会话 ID
- `question_id`：要追问的原始问题 ID
- `answer`：候选人对该题的回答

响应语义：

- `follow_up_questions`：追问列表
- `reason`：为什么这样追问
- `workflow_trace`：节点执行轨迹，例如 `answer_analysis_node -> follow_up_node`

## 工作流总览

题目生成链路：

```
InterviewQuestionRequest
  -> resume_parse_node
  -> job_profile_node
  -> question_generation_node
  -> InterviewSessionResponse
```

追问链路：

```
InterviewFollowUpRequest
  -> answer_analysis_node
  -> follow_up_node
  -> InterviewFollowUpResponse
```

评分报告链路：

```
AnswerSubmissionRequest
  -> answer_analysis_node
  -> follow_up_node
  -> scoring_node
  -> report_node
  -> InterviewReportResponse
```

## 完成标准

- 题目生成响应返回 `workflow_trace`
- 题目生成包含岗位画像节点生成的 `job_profile` 类型题目
- `/interviews/follow-up` 能生成追问并保存到数据库
- 其他用户不能对不属于自己的面试会话生成追问
- 评分报告响应返回完整节点 trace
- 阶段四迁移可创建追问表
- 项目代码语法检查通过

## 文档索引

| 文档 | 内容 |
|------|------|
| [01-图式工作流设计](01-图式工作流设计.md) | 为什么拆节点、状态如何流转、如何迁移到真实 LangGraph |
| [02-节点说明](02-节点说明.md) | 每个节点的输入、输出、所在 `.py` 路径 |
| [03-追问接口与持久化](03-追问接口与持久化.md) | `/interviews/follow-up`、service、ORM 和迁移 |
| [04-测试与验收](04-测试与验收.md) | 阶段四测试覆盖、验证命令和当前环境说明 |
