# Section_7_压测与量化

## 🎯 学习目标

1. 掌握 **Locust 压测框架**的使用（用户模拟、任务定义、压测策略）
2. 理解核心性能指标（QPS、RPS、延迟分布 P50/P90/P99、错误率）
3. 学会对 FastAPI + RAG 系统进行压测并量化优化效果
4. 掌握瓶颈定位方法（数据库、向量检索、LLM 调用、网络 I/O）

## 📚 前置知识

- FastAPI 异步编程（Section_4）
- Redis 缓存与连接池（Section_1）
- PostgreSQL 连接池优化（Section_2）
- 批处理优化技术（Section_6）

## 📂 文件说明

按以下顺序学习：

### 1️⃣ demo1_locust_basics.py
- **Locust 基础使用** - HttpUser、任务定义、权重、等待时间
- **压测指标解读** - QPS/RPS、响应时间、百分位数
- **Web UI 使用** - http://localhost:8089

### 2️⃣ demo2_fastapi_stress_test.py
- **FastAPI 压测实战** - 对真实 API 进行压测
- **性能瓶颈定位** - 数据库连接、异步优化、缓存命中率
- **优化前后对比** - 量化优化效果

### 3️⃣ demo3_rag_performance_test.py
- **RAG 系统压测** - Embedding + 向量检索 + LLM 生成
- **性能分析** - 各环节耗时占比、并发能力
- **生产级指标** - P99 延迟、错误率、吞吐量

## 🚀 运行方式

### 安装依赖
```bash
pip install locust fastapi uvicorn redis psycopg2-binary sqlalchemy
```

### 运行 Demo1（Locust 基础）
```bash
# 终端1：启动被测服务
python demo1_locust_basics.py

# 终端2：启动 Locust 压测
locust -f demo1_locust_basics.py --host=http://localhost:8000

# 浏览器访问 http://localhost:8089
# 设置用户数（如 100）和增长速率（如 10/s）
```

### 运行 Demo2（FastAPI 压测）
```bash
# 终端1：启动 FastAPI 服务
python demo2_fastapi_stress_test.py

# 终端2：启动压测
locust -f demo2_fastapi_stress_test.py --host=http://localhost:8001
```

### 运行 Demo3（RAG 压测）
```bash
# 确保 Redis、PostgreSQL 已启动
python demo3_rag_performance_test.py
locust -f demo3_rag_performance_test.py --host=http://localhost:8002
```

## ⚠️ 注意事项

1. **压测环境隔离** - 不要对生产环境压测，使用本地或测试环境
2. **逐步加压** - 从小并发开始（10 用户），逐步增加观察系统表现
3. **资源监控** - 压测时监控 CPU、内存、数据库连接数、Redis 连接数
4. **数据准备** - 提前准备测试数据，避免冷启动影响测试结果
5. **多次测试** - 每次压测至少持续 3-5 分钟，取多次测试的平均值

## 📊 核心指标解读

| 指标 | 说明 | 生产级标准 |
|------|------|------------|
| **QPS/RPS** | 每秒请求数/响应数 | > 100（简单查询），> 10（RAG 查询） |
| **P50 延迟** | 50% 请求的响应时间 | < 100ms（简单查询），< 2s（RAG） |
| **P90 延迟** | 90% 请求的响应时间 | < 200ms（简单查询），< 3s（RAG） |
| **P99 延迟** | 99% 请求的响应时间 | < 500ms（简单查询），< 5s（RAG） |
| **错误率** | 失败请求占比 | < 0.1% |
| **吞吐量** | 单位时间处理的数据量 | 根据业务需求 |

## 🔍 瓶颈定位思路

1. **数据库瓶颈** - 连接池耗尽、慢查询、索引缺失
2. **向量检索瓶颈** - HNSW 索引参数、检索批次大小
3. **LLM 调用瓶颈** - 并发限制、token 限流、网络延迟
4. **缓存未命中** - Redis 缓存策略、过期时间设置
5. **异步未充分利用** - 同步阻塞调用、未使用 asyncio

## 🎓 学习重点

- Locust 的 `HttpUser`、`@task`、`wait_time` 用法
- 如何读懂 Locust Web UI 的性能报告
- P50/P90/P99 百分位数的含义和重要性
- 如何通过压测定位系统瓶颈
- 优化前后的性能对比量化方法

## 📖 推荐阅读

- [Locust 官方文档](https://docs.locust.io/)
- [性能测试最佳实践](https://martinfowler.com/articles/performance-testing.html)
- [百分位数 vs 平均值](https://www.elastic.co/blog/averages-can-dangerous-use-percentile)

## ⏭️ 下一步

完成本节后，你将掌握完整的性能优化与压测技能栈：
- Week_5 将进入前端开发、认证、监控与部署
- 本周是第4周最后一节，完成后可进行 **Week 4 综合复习**

---

**输入【答疑】解决疑惑 | 输入【继续】进入下一周**
