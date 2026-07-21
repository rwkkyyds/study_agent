# Section 5: Agent Memory 记忆机制

## 学习目标
1. 理解 Agent 的三种记忆类型：短期、长期、工作记忆
2. 掌握 LangGraph 的 Checkpoint 机制（MemorySaver）
3. 用 Redis 实现会话持久化（生产级方案）

## 前置知识
- Section 2: LangGraph StateGraph、State、Node
- Section 4: SQLAlchemy（数据库操作思路）

## 技术栈
- **框架**: LangGraph 1.x（内置 Checkpoint）
- **存储**: MemorySaver（开发）/ Redis（生产）
- **模式**: Thread-based 会话管理

## Agent 的三种记忆

```
短期记忆（Short-term）    → 当前会话的消息历史（messages 列表）
  - 每次对话自动累积
  - 会话结束即丢失
  - 用 LangGraph State.messages 管理

工作记忆（Working）       → 当前任务的状态（State 中间结果）
  - Agent 推理过程中的临时数据
  - 用 LangGraph State 管理
  - 支持 Checkpoint 持久化

长期记忆（Long-term）     → 跨会话的知识（用户偏好、历史总结）
  - 存储在 Redis/数据库中
  - 每次会话开始时加载
  - 需要手动管理
```

## 代码结构

### demo1_memory_basics.py（LangGraph Checkpoint）
1. MemorySaver 基础用法
2. Thread-based 会话（同一用户多轮对话）
3. State 持久化与恢复
4. 会话历史查询

### demo2_redis_memory.py（Redis 会话持久化）
1. Redis 连接与基本操作
2. 存储/读取会话历史
3. 跨会话记忆恢复
4. 会话过期与清理

## 运行顺序

```bash
# Step 1: 理解 LangGraph Checkpoint 机制（无需 Redis）
python demo1_memory_basics.py

# Step 2: Redis 会话持久化（需要 Redis 服务）
python demo2_redis_memory.py
```

## 注意事项
- demo1 使用 MemorySaver（内存），无需外部依赖
- demo2 需要 Redis 服务运行（`docker run -d -p 6379:6379 redis`）
- 生产环境建议用 LangGraph 的 RedisCheckpointer
