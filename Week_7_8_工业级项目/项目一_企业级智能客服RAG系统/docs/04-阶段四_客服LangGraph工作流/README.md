# 阶段四：客服 LangGraph 工作流

## 阶段目标

将阶段三的 `Retriever` 组装为客服 Agent Tool，并使用 LangGraph 编排意图分类、条件路由、知识库搜索、订单查询和转人工。

## 阅读顺序

1. `01-阶段四概述.md`：理解目标、边界和整体链路。
2. `02-客服工具设计.md`：理解工具职责和数据写入边界。
3. `03-LangGraph工作流.md`：理解状态、节点和条件边。
4. `04-ChatAPI与测试.md`：运行接口和工作流测试。

## 代码入口

- `app/workflow/customer_service.py`：`CustomerServiceWorkflow` 和 `IntentClassifier`。
- `app/tools/customer_service.py`：知识库、订单、转人工工具。
- `app/schemas/chat.py`：Chat 请求与响应模型。
- `app/api/chat.py`：需要 JWT 的 `POST /chat`。
- `tests/test_workflow.py`：5 个工作流测试。
- `tests/test_chat.py`：3 个 Chat API 测试。

## 运行验证

```powershell
C:\Users\admin\Desktop\agent_study\.venv\Scripts\python.exe -m pytest tests/test_workflow.py tests/test_chat.py -v
C:\Users\admin\Desktop\agent_study\.venv\Scripts\python.exe -m pytest tests/ -v
```

## 当前实现边界

当前阶段使用关键词分类器和订单查询本地替身，保证无外部 LLM 和订单系统时可运行。知识库检索复用阶段三 `Retriever`，转人工使用阶段二 `Ticket` 和 `Message` 模型创建工单。

## 完成标准

- 三类意图可以稳定路由。
- 知识库路径返回召回来源。
- 订单路径返回结构化订单结果。
- 人工路径创建工单和系统消息。
- `/chat` 必须经过 JWT 身份认证。
- 阶段四测试和全量回归测试通过。
