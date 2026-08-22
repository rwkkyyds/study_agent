# 01 - SSE 接口设计

> 关键路径：`app/api/interviews.py`、`app/services/auth.py`、`app/schemas/interview.py`、`app/services/interviews.py`

## 为什么阶段六要做 SSE

面试系统里最适合流式输出的是追问过程。

题目生成通常是一次性结果，评分报告也适合一次性返回结构化 JSON；但追问更接近真实面试场景：候选人刚回答完一道题，面试官先分析回答，再逐步给出追问。

SSE 的价值在于：

- 浏览器实现简单，原生 `EventSource` 就能消费
- 后端只需要返回 `text/event-stream`
- 适合服务端主动推送阶段性事件
- 比 WebSocket 更轻量，适合单向输出

阶段六用 SSE 输出追问生成过程，而不是把所有接口都改成流式接口。这样能保持系统边界清晰：题目生成和评分报告继续走 JSON API，追问体验走 SSE。

## 接口一：创建 stream token

文件路径：`app/api/interviews.py`

接口：

- `POST /interviews/follow-up/stream-token`

这个接口仍然使用普通 Bearer JWT 登录态。它的职责不是生成追问，而是确认当前用户有权访问这个面试会话，并为后续 SSE 连接签发短期 token。

请求模型来自 `app/schemas/interview.py`：

- `FollowUpStreamTokenRequest`

核心字段：

- `session_id`：面试会话 ID
- `question_id`：当前作答题目 ID
- `answer`：候选人对这道题的回答

响应模型来自 `app/schemas/interview.py`：

- `FollowUpStreamTokenResponse`

核心字段：

- `stream_token`：短期 SSE token
- `token_type`：保持 bearer 语义
- `expires_in`：有效秒数，默认 300 秒

## 接口二：打开 SSE 流

文件路径：`app/api/interviews.py`

接口：

- `GET /interviews/follow-up/stream?token=...`

这个接口不再读取 `Authorization` 请求头，而是读取 query 中的短期 token。原因是浏览器原生 `EventSource` 不能设置自定义请求头。

接口返回类型：

- `StreamingResponse`
- `media_type="text/event-stream"`

输出事件：

- `trace`
- `follow_up`
- `done`
- `error`

## token 设计

文件路径：`app/services/auth.py`

阶段六新增的 stream token 和普通登录 JWT 使用同一套签名密钥与算法，但 payload 更严格。

payload 必须包含：

- `purpose`：固定为追问 SSE 场景
- `sub`：用户 ID
- `session_id`：面试会话 ID
- `question_id`：题目 ID
- `answer`：候选人回答
- `exp`：过期时间

学习重点是 `purpose` 字段。它用于区分“登录 token”和“流式连接 token”。即使两者都由 JWT 表达，也不能混用，否则任何 access token 都可能被拿来打开 SSE。

## 会话归属校验

文件路径：`app/services/interviews.py`

阶段二到五已经实现了用户隔离。阶段六延续这个原则：

- 创建 stream token 时，根据当前登录用户校验 `session_id`
- 打开 SSE 时，根据 stream token 中的 `sub` 和 `session_id` 再查一次会话

这两次校验覆盖了两个风险点：

- 其他用户不能给你的会话创建 token
- 伪造或过期 token 不能打开流式接口

`InterviewPersistenceService` 新增公开方法用于归属校验，API 层不再直接调用私有方法。这样 service 的内部实现可以保持封装，API 只依赖明确的业务能力。

## 追问持久化边界

文件路径：`app/services/interviews.py`

SSE 端点没有重新写一套追问落库逻辑，而是复用已有的 `generate_follow_up` 业务能力。

这样做有三个好处：

- `/interviews/follow-up` 和 `/interviews/follow-up/stream` 的结果一致
- `InterviewFollowUp` 的写入规则保持一致
- `InterviewSession.status` 更新规则保持一致

阶段六的新增点是“如何输出过程”，不是“重新定义追问业务”。

## Qwen 追问增强边界

文件路径：`app/services/qwen_llm.py`、`app/workflow/interview_graph.py`

通义千问增强只接入工作流节点，不接入 API 层。API 层仍然调用 `InterviewPersistenceService.generate_follow_up`，所以普通 JSON 追问和 SSE 追问共享同一条业务链路。

启用条件是：

- `LLM_PROVIDER=qwen`
- `DASHSCOPE_API_KEY` 存在

如果 Qwen 调用失败，工作流会保留本地规则追问，并在 trace 中记录 `qwen_follow_up_enrichment_skipped`。这样浏览器端仍然能收到 `trace`、`follow_up`、`done` 事件，不会因为外部 LLM 不稳定导致面试流程中断。

## 错误处理

非法 token、过期 token、用途不匹配 token 都返回 401。

非本人会话在创建 token 阶段返回 404。这和已有 `/interviews/follow-up`、`/interviews/evaluate` 的用户隔离语义一致：对当前用户来说，这个会话不存在。

SSE 生成过程中如果出现异常，会输出 `error` 事件。浏览器页面可以把它展示在事件列表里，而不是让页面静默失败。
