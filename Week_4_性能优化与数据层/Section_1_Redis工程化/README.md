# Section 1: Redis 工程化

## 学习目标
1. 掌握 Redis 基础数据结构（String/Hash/List/Set）
2. 实现缓存策略（Cache-Aside、TTL、缓存失效）
3. 用 Redis 实现会话存储（Agent 对话历史持久化）
4. 用 Redis 实现限流（滑动窗口算法）
5. 了解 Pub/Sub 消息机制

## 前置知识
- Section 5（Week3）：Agent Memory、MemorySaver 概念
- Section 4（Week3）：PostgreSQL 基础（对比关系型 vs 缓存）

## 技术栈
- **Redis**: Docker 部署
- **Python**: redis-py 库（组件，不造轮子）
- **场景**: 缓存 / 会话 / 限流 / Pub/Sub

## 代码结构

### demo1_redis_basics.py（Redis 基础操作）
1. Redis 连接与 Ping
2. String：SET/GET/SETEX/INCR ----->  incr音标:/ɪnˈkrɪmɪnt/
3. Hash：HSET/HGETALL/HINCRBY
4. List：LPUSH/RPOP/LRANGE
5. Set：SADD/SMEMBERS/SINTER   

### demo2_redis_cache.py（缓存策略）
1. Cache-Aside 模式（旁路缓存）
2. TTL 过期策略
3. 缓存穿透/击穿/雪崩概念
4. 与 LLM 调用结果缓存集成

### demo3_redis_session.py（会话存储）
1. Redis 存储 Agent 对话历史
2. 会话 TTL 自动过期
3. 会话列表与删除
4. 替代 MemorySaver 的生产方案

### demo4_redis_ratelimit.py（限流 + Pub/Sub）
1. 滑动窗口限流算法
2. 固定窗口限流
3. Redis Pub/Sub 基础
4. 限流 + Agent 集成示例

## 运行顺序

```bash
# 前置：启动 Redis
docker run -d -p 6379:6379 --name redis-demo redis

# Step 1: Redis 基础
pip install redis
python demo1_redis_basics.py

# Step 2: 缓存策略
python demo2_redis_cache.py

# Step 3: 会话存储
python demo3_redis_session.py

# Step 4: 限流 + Pub/Sub
python demo4_redis_ratelimit.py
```

## 注意事项
- 需要先启动 Redis 服务（Docker 或本地安装）
- 所有 demo 使用 redis-py 库（有组件用组件）
- demo 中的 key 都加了前缀，避免污染
