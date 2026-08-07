# 03 LangGraph 工作流

## 1. 状态定义

`CustomerServiceState` 包含：

- `customer_id`：已认证用户 ID。
- `query`：用户问题。
- `intent`：`knowledge`、`order` 或 `human`。
- `answer`：最终客服文本。
- `sources`：知识库来源及相似度。
- `order`：订单查询结构化结果。
- `ticket_id`：人工工单 ID。

## 2. 节点

```text
START
  ↓
classify_intent
  ├─ knowledge → knowledge_search → END
  ├─ order     → order_lookup     → END
  └─ human     → transfer_to_human → END
```

分类器当前采用确定性关键词规则，优先级为人工 > 订单 > 知识库，避免“请转人工查询订单”被错误分流到订单路径。模型分类器可以实现相同的 `classify(query) -> Intent` 契约后替换。

## 3. 为什么使用 StateGraph

`StateGraph` 将节点、状态和条件边显式化：可以单独测试每个节点，可以在阶段五增加重试和降级节点，也可以在后续加入人工审批或多轮记忆，而不把流程堆叠在一个 API 函数中。

## 4. 异常边界

当前阶段对空查询在工作流入口快速失败；阶段五将为知识库、订单服务和数据库写入增加超时、重试、熔断和降级，并记录每个节点的耗时和结果。
