# Section 4: PostgreSQL 基础

## 学习目标
1. 掌握 SQLAlchemy ORM（模型定义、会话管理、CRUD 操作）
2. 理解数据模型设计（字段类型、索引、约束）
3. 掌握事务机制（BEGIN/COMMIT/ROLLBACK）
4. 了解 Alembic 数据库迁移
5. 用 FastAPI + SQLAlchemy 构建用户系统

## 前置知识
- Week 1: FastAPI 路由、Pydantic
- Python 基础：类、装饰器、上下文管理器

## 技术栈
- **ORM**: SQLAlchemy 2.x
- **迁移**: Alembic
- **数据库**: SQLite（Demo）/ PostgreSQL（生产）
- **异步驱动**: asyncpg（PostgreSQL）/ aiosqlite（SQLite）

## SQLAlchemy 是什么？

```
直接写 SQL：                    用 SQLAlchemy：
  cursor.execute(                user = User(name="张三")
    "INSERT INTO users           session.add(user)
     (name) VALUES ('张三')")     session.commit()
  → SQL 注入风险                  → 安全，自动生成参数化 SQL
  → 换数据库要改代码              → 换数据库只改连接字符串
  → 字符串拼接容易出错            → Python 对象操作，IDE 有提示
```

## 核心概念

```
Model（模型）   → Python 类，对应数据库表
Session（会话） → 数据库连接的"工作区"，跟踪所有变更
Engine（引擎）  → 数据库连接池，管理实际连接
Migration（迁移）→ 版本化的数据库结构变更
```

### 通俗理解：Session vs Engine

**Engine（引擎）= 停车场管理系统**
- 负责维护数据库连接池（复用连接）
- 一个项目通常**只有 1 个 Engine**
- 作用：**分配连接、回收连接、管理连接生命周期**
- 特点：静态、被动、配置型

**Session（会话）= 停车条/借书单**
- 记录你这次操作的所有变更（新增、修改、删除）
- 每次数据库操作都要**创建一个新 Session**
- 作用：**追踪变更、支持事务 (BEGIN/COMMIT/ROLLBACK)**
- 特点：动态、主动、执行型

| 操作 | 对应比喻 | 代码示例 |
|------|--------|--------|
| 创建连接 | 去停车场前台领号 | `engine = create_engine("...")` |
| 开启工作区 | 拿停车条去停车 | `session = Session(engine)` |
| 记录变更 | 在停车条上写操作 | `session.add(user)` |
| 提交变更 | 交停车条给前台 | `session.commit()` |
| 放弃变更 | 说"我不停了" | `session.rollback()` |
| 关闭工作区 | 停车完成离开 | `session.close()` |

## 代码结构

### demo1_sqlalchemy_basics.py（ORM 基础）
1. 定义 Model（User 表）
2. 创建表（create_all）
3. CRUD 操作（增删改查）
4. 事务演示
5. 索引与约束

### demo2_fastapi_user_system.py（FastAPI + SQLAlchemy）
1. 数据库连接配置
2. Pydantic Schema ↔ SQLAlchemy Model 转换
3. 用户注册/登录/查询 API
4. 依赖注入数据库会话

## 运行顺序

```bash
# Step 1: 理解 SQLAlchemy ORM 基础（SQLite，无需安装 PostgreSQL）
python demo1_sqlalchemy_basics.py

# Step 2: FastAPI + SQLAlchemy 用户系统
python demo2_fastapi_user_system.py
```

## 注意事项
- Demo 使用 SQLite（零配置），生产环境换 PostgreSQL 只需改连接字符串
- SQLAlchemy 2.x 推荐使用 `select()` 而非 `query()`
- Alembic 迁移命令在学习笔记中讲解
