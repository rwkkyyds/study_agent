# 阶段五：企业级稳定性

> 在阶段四客服工作流上增加限流、会话记忆、重试、熔断、降级和指标能力，让系统从“功能可用”进入“故障可控”。

## 一、为什么阶段四之后先做稳定性

阶段四已经能够完成一次客服请求，但请求链路仍然有几个生产风险：

- 同一个用户可以无限频繁调用 `/chat`，可能耗尽线程、模型额度或订单服务配额。
- 多轮对话没有统一的短期记忆边界，无法控制历史长度和过期时间。
- Redis、订单服务、LLM 或向量数据库出现网络故障时，系统缺少明确的失败策略。
- 没有统一指标，无法回答请求量、429 数量和意图分布等运行问题。

阶段五不改变阶段四的业务路由契约，而是在 API 入口和外部依赖边界补充保护措施。

## 二、本阶段架构

```text
客户端
  │
  ▼
JWT 身份校验
  │
  ▼
POST /chat
  │
  ├── 用户 ID 限流
  │      ├── 超限 → 429 + Retry-After
  │      └── 通过
  │
  ├── 保存 user 消息
  │
  ├── CustomerServiceWorkflow
  │      ├── knowledge → Retriever
  │      ├── order     → 订单适配器
  │      └── human     → Ticket + Message
  │
  ├── 保存 assistant 消息
  └── 记录 Metrics

Redis 可用 ──→ 共享限流 + 共享会话记忆
Redis 不可用 ──→ 进程内回退，保证本地开发可运行
```

## 三、本阶段交付物

| 类型 | 文件 | 作用 |
|------|------|------|
| 稳定性组件 | `app/stability/rate_limit.py` | 滑动窗口限流，支持 Redis 和进程内回退 |
| 稳定性组件 | `app/stability/memory.py` | 会话消息保存、读取、裁剪和清理 |
| 稳定性组件 | `app/stability/resilience.py` | 有限重试、指数退避和熔断器 |
| 稳定性组件 | `app/stability/metrics.py` | 输出 Prometheus 文本指标 |
| 工厂 | `app/stability/factory.py` | 创建 Redis 客户端和稳定性组件 |
| API 接入 | `app/api/chat.py` | 为 `/chat` 增加限流、记忆和指标记录 |
| 监控接口 | `app/main.py` | 提供 `GET /metrics` |
| 配置 | `app/core/config.py` | Redis、限流、会话参数配置 |
| 测试 | `tests/test_stability.py` | 验证限流、记忆、指标、重试和熔断 |

## 四、推荐学习顺序

1. 先读 [01-稳定性架构](01-稳定性架构.md)，理解请求链路和组件边界。
2. 再读 [02-重试熔断与降级](02-重试熔断与降级.md)，理解故障分类和保护策略。
3. 最后读 [03-测试与运行](03-测试与运行.md)，执行专项测试和全量回归。

## 五、运行方式

项目默认不配置 `REDIS_URL`，因此测试和本地开发不需要启动 Redis。使用项目虚拟环境执行：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest tests/test_stability.py -v
.venv\Scripts\python.exe -m pytest tests/ -v
```

生产或多实例环境可以配置：

```text
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
SESSION_TTL_SECONDS=3600
SESSION_MAX_MESSAGES=20
```

## 六、完成标准

- 单用户超过限流阈值后返回 `429`，并包含 `Retry-After`。
- 不同用户的限流计数相互隔离。
- 会话消息只保留最近配置数量，并支持 TTL。
- Redis 未配置或连接失败时，应用仍能启动并使用本地回退。
- 重试次数有限，失败达到阈值后熔断。
- `/metrics` 能输出请求总数、429 数量、状态码和意图指标。
- 阶段五专项测试通过，且阶段一到四测试不回归。

## 七、当前不实现

- Redis Sentinel 或 Redis Cluster 高可用编排。
- 分布式锁和跨区域流量治理。
- 完整 OpenTelemetry exporter 和 Grafana 仪表盘。
- 真实订单服务、LLM 服务和 Milvus 客户端的生产适配。

这些能力将在部署阶段或接入真实基础设施时继续实现。
