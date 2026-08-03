# 阶段一：项目骨架

> 建立 FastAPI 应用基础框架，可启动、可测试。

## 阶段目标

- 搭建 FastAPI 应用入口，支持 lifespan 生命周期管理
- 建立环境变量配置体系（Pydantic Settings）
- 配置 SQLite 数据库会话（SQLAlchemy 2.0）
- 提供 `/health` 和 `/version` 两个基础接口
- 编写 pytest 测试基线，保证可重复验证

## 涉及文件

| 文件 | 说明 |
|------|------|
| `app/__init__.py` | 应用包标记，空文件 |
| `app/core/__init__.py` | core 包标记 |
| `app/core/config.py` | Settings 类：集中管理环境变量 |
| `app/db/__init__.py` | db 包标记 |
| `app/db/session.py` | SQLAlchemy 引擎、会话工厂、Base 基类 |
| `app/main.py` | FastAPI 入口，lifespan 管理，路由注册 |
| `tests/test_health.py` | 健康检查接口测试 |
| `.env.example` | 环境变量配置模板 |
| `requirements.txt` | 项目依赖清单 |

## 完成标准

- 应用可以启动：`uvicorn app.main:app --reload`
- `/health` 返回 `{"status": "ok", "environment": "development"}`
- `/version` 返回 `{"app": "enterprise-customer-service-rag", "version": "0.1.0"}`
- 配置不依赖硬编码密钥
- pytest 测试通过（2 passed）

## 文档索引

| 文档 | 内容 |
|------|------|
| [01-应用入口详解](01-应用入口.md) | main.py 各组件说明 |
| [02-配置管理详解](02-配置管理.md) | config.py 配置体系 |
| [03-数据库会话详解](03-数据库会话.md) | session.py 数据库连接 |
| [04-接口与测试详解](04-接口与测试.md) | health/version 接口 + 测试 |
| [05-项目脚手架说明](05-项目脚手架说明.md) | 目录结构、运行方式、依赖 |
| [06-请求流程](06-请求流程.md) | 一次请求的完整生命周期 |