# 阶段四：客服 LangGraph 工作流

> 将阶段三的检索能力和阶段二的工单模型组装成可路由的客服工作流。

## 一、为什么阶段三之后做工作流

阶段三只能回答“如何找到相似知识片段”，还不能根据用户意图选择不同业务动作。客服请求至少存在三条不同路径：

- 知识问题：搜索知识库并返回来源。
- 订单问题：调用订单查询适配器。
- 复杂投诉或明确转接：创建人工客服工单。

如果把这些逻辑全部写在 API 路由中，路由会同时承担分类、检索、数据库写入和响应转换，后续替换分类器或订单服务会很困难。因此本阶段用 LangGraph 把状态、节点和条件边拆开。

## 二、本阶段架构

```text
客户端
  │
  ▼
POST /chat
  │
  ▼
JWT get_current_user
  │
  ▼
CustomerServiceWorkflow
  │
  ▼
classify_intent
  │
  ├── knowledge → knowledge_search → Retriever → ChatResponse
  ├── order     → order_lookup     → OrderResult → ChatResponse
  └── human     → transfer_to_human → Ticket + Message → ChatResponse
```

## 三、状态图如何工作

```text
START
  ↓
classify_intent
  ├── knowledge → knowledge_search → END
  ├── order     → order_lookup → END
  └── human     → transfer_to_human → END
```

`CustomerServiceState` 保存 `customer_id`、`query`、`intent`、`answer`、`sources`、`ticket_id` 和 `order` 等字段。每个节点只写入自己负责的字段，工作流最后返回统一状态。

当前分类器是确定性关键词分类器，优先级为人工 > 订单 > 知识库。这样“请转人工查询订单”会优先进入人工路径。后续可以实现相同 `classify(query) -> Intent` 契约的 LLM 分类器进行替换。

## 四、分层职责

- API 层：校验请求、注入 JWT 用户和工作流、转换响应。
- Schema 层：限制问题长度，定义响应结构。
- Workflow 层：管理状态图、节点和条件路由。
- Tools 层：封装知识检索、订单适配和工单创建。
- RAG 层：复用阶段三 Retriever，不复制向量化逻辑。
- Model 层：复用阶段二 Ticket 和 Message 的持久化关系。

## 五、安全边界

人工转接使用 JWT 校验得到的 `current_user.id`，不能从客户端请求体接收任意 `customer_id`。知识库和订单查询在生产环境还需要增加租户过滤、用户权限和数据脱敏。

API 不直接操作向量库，也不直接拼接工单 SQL。工作流只负责编排，工具负责单一领域动作，模型负责数据映射。

## 六、代码入口

- `app/workflow/customer_service.py`：`CustomerServiceWorkflow` 和 `IntentClassifier`。
- `app/tools/customer_service.py`：知识库、订单、转人工工具。
- `app/schemas/chat.py`：Chat 请求与响应 Schema。
- `app/api/chat.py`：JWT 保护的 `POST /chat`。
- `tests/test_workflow.py`：意图、路由、工单和空查询测试。
- `tests/test_chat.py`：认证、知识路径和请求校验测试。

## 七、运行验证

```powershell
.venv\Scripts\python.exe -m pytest tests/test_workflow.py tests/test_chat.py -v
.venv\Scripts\python.exe -m pytest tests/ -v
```

## 八、完成标准

- 三类意图可以稳定路由。
- 知识库路径返回回答和召回来源。
- 订单路径返回结构化订单结果。
- 人工路径创建工单和系统消息。
- `/chat` 必须经过 JWT 身份认证。
- 阶段四专项测试和全量回归测试通过。

## 九、当前边界

当前使用关键词分类器和本地订单查询替身，保证没有外部 LLM 和订单系统时仍可运行。阶段五会在 `/chat` 外围增加限流、会话记忆、指标和故障降级，但不改变本阶段的三路工作流契约。
