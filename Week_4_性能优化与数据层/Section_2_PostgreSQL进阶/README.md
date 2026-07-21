# Section 2: PostgreSQL 进阶

## 学习目标
1. 掌握 PostgreSQL 索引类型与优化策略（B-tree、GIN、GiST、部分索引、覆盖索引）
2. 理解连接池原理与 SQLAlchemy 连接池配置
3. 学会用 EXPLAIN ANALYZE 分析查询性能
4. 解决 N+1 查询问题（Eager Loading）
5. 掌握高级查询：窗口函数、CTE、子查询优化

## 前置知识
- Week3 Section4: PostgreSQL 基础（SQLAlchemy ORM、CRUD、事务）
- Week4 Section1: Redis 工程化

## 技术栈
- **ORM**: SQLAlchemy 2.x
- **数据库**: PostgreSQL 17（全部 demo 直连 PostgreSQL）
- **驱动**: psycopg2-binary（同步）

## 环境要求
- PostgreSQL 已启动，用户 `postgres`，密码 `123456`
- 已安装依赖：`pip install sqlalchemy psycopg2-binary`

## 代码结构

| 文件 | 内容 | 核心知识点 |
|------|------|-----------|
| demo1_index_types.py | 索引类型与优化 | B-tree/复合索引/部分索引/覆盖索引/GIN(JSONB)/EXPLAIN ANALYZE |
| demo2_connection_pool.py | 连接池配置与监控 | pool_size/max_overflow/并发线程/同步vs异步连接池 |
| demo3_query_analysis.py | 查询性能分析 | N+1问题/joinedload/selectinload/EXPLAIN ANALYZE |
| demo4_advanced_queries.py | 高级查询 | ROW_NUMBER/RANK/LAG/CTE/Top-N问题 |

## 运行顺序

```bash
# Step 1: 索引类型与优化（10万条数据，EXPLAIN ANALYZE 真实执行计划）
python demo1_index_types.py

# Step 2: 连接池配置与监控（连接复用、并发线程、参数速查）
python demo2_connection_pool.py

# Step 3: 查询性能分析（N+1 问题演示 + Eager Loading 解决方案）
python demo3_query_analysis.py

# Step 4: 高级查询（窗口函数 + CTE + Top-N 经典面试题）
python demo4_advanced_queries.py
```

## 注意事项
- 所有 demo 直连 PostgreSQL，需要先启动 PostgreSQL 服务
- demo1 会创建 10 万条测试数据，运行后会自动清理
- demo2 会创建临时测试表，运行后会自动清理
- 所有 demo 独立运行，互不依赖

## 下一节预告
Section 3: pgvector 向量扩展（向量字段、向量索引、混合检索）
