# 04 Chat API 与测试

## 1. API 契约

### `POST /chat`

请求头：

```http
Authorization: Bearer <JWT>
Content-Type: application/json
```

请求体：

```json
{"query": "退款规则是什么？"}
```

成功响应示例：

```json
{
  "answer": "退款申请需要提交订单号和退款原因。",
  "intent": "knowledge",
  "sources": [{"id": "chunk-1", "score": 0.91, "metadata": {}}],
  "ticket_id": null,
  "order": null
}
```

## 2. 状态码

- `200`：工作流成功完成。
- `401`：缺少或无效 JWT。
- `422`：请求体缺失、问题为空或超过 2000 字符。
- `500`：未处理的基础设施异常，阶段五会增加统一错误处理和降级。

## 3. 测试策略

- `test_workflow.py`：验证分类器、知识库路由、订单路由、转人工工单和空查询。
- `test_chat.py`：验证 JWT 保护、成功响应和 Pydantic 输入校验。
- 全量测试：确认阶段一至阶段三无回归。

## 4. 手工验证

启动应用：

```powershell
uvicorn app.main:app --reload
```

先通过 `/auth/register` 和 `/auth/login` 获取 Token，再访问 `/docs` 调用 `POST /chat`。当前知识库默认为空，因此知识路径会返回“暂未找到相关内容”；阶段五将增加知识库入库接口和持久化索引。
