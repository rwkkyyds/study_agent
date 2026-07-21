# Section 6: Agent 工具调用异常处理、重试与降级策略

## 学习目标
1. 理解 Agent 工具调用中常见的异常类型
2. 掌握重试策略（指数退避、最大重试次数）
3. 掌握降级策略（Fallback 工具、优雅降级）
4. 用 LangGraph 构建带容错能力的 Agent 工作流

## 前置知识
- Section 1: Agent 与 ReAct 框架基础
- Section 2: LangGraph StateGraph、条件路由
- Section 5: Agent Memory（State 管理）

## 技术栈
- **框架**: LangGraph 1.x
- **重试**: tenacity 库（生产级重试组件）
- **模式**: try-except + 重试 + 降级三级容错

## 为什么需要异常处理？

Agent 调用工具时可能遇到：
```
工具执行失败    → API 超时、网络断开、权限不足
返回格式错误    → 工具返回非预期格式，LLM 无法解析
工具不存在      → LLM 幻觉调用不存在的工具
参数错误        → LLM 生成了错误的工具参数
限流/配额耗尽   → API 返回 429 Too Many Requests
```

## 容错三级体系

```
第一级：异常捕获（try-except）    → 防止 Agent 崩溃
第二级：自动重试（retry）        → 应对临时故障（网络抖动、限流）
第三级：优雅降级（fallback）     → 重试失败后提供兜底方案
```

## 代码结构

### demo1_exception_basics.py（异常捕获基础）
1. 工具调用的常见异常类型
2. try-except 捕获工具执行错误
3. LangGraph 中用 State 传递错误信息
4. 错误信息反馈给 LLM 自动修正

### demo2_retry_strategy.py（重试策略）
1. tenacity 库基础用法
2. 指数退避重试（exponential backoff）
3. 按异常类型选择性重试
4. 与 LangGraph Agent 集成

### demo3_fallback_degrade.py（降级策略）
1. Fallback 工具注册（主工具失败 → 切换备用工具）
2. 优雅降级（返回部分结果 + 错误提示）
3. LangGraph 条件路由实现降级分支
4. 完整容错 Agent 工作流

## 运行顺序

```bash
# Step 1: 理解异常捕获基础
python demo1_exception_basics.py

# Step 2: 掌握重试策略（安装 tenacity）
pip install tenacity
python demo2_retry_strategy.py

# Step 3: 掌握降级策略
python demo3_fallback_degrade.py
```

## 注意事项
- demo1 使用模拟工具，无需外部 API
- demo2 需要安装 tenacity：`pip install tenacity`
- demo3 综合运用三级容错，是本节重点
- 所有 demo 均使用 try-except + logging，符合工程规范
