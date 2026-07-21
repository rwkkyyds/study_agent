# Section 1: FastAPI 入门

## 学习目标

- 理解 FastAPI 框架核心概念
- 掌握路由定义、请求参数处理
- 理解异步 I/O（async/await）基础
- 掌握 Pydantic 数据校验模型

## 前置知识

- Python 基础语法
- HTTP 协议基础概念（GET/POST、状态码、JSON）

## 学习顺序

1. 先运行 `demo1_fastapi_hello.py` — 感受最简 FastAPI 服务
2. 再运行 `demo2_fastapi_param.py` — 学习参数处理与 Pydantic 校验
3. 阅读代码注释，理解每一行的作用

## 代码运行方式

```bash
# 安装依赖
pip install fastapi uvicorn

# 运行 demo1
python demo1_fastapi_hello.py

# 运行 demo2
python demo2_fastapi_param.py
```

运行后访问 `http://127.0.0.1:8000/docs` 查看自动生成的 API 文档。

## 注意事项

- FastAPI 使用 `uvicorn` 作为 ASGI 服务器
- `async def` 定义的路由会自动使用异步模式
- Pydantic 模型用于自动校验请求体数据

## 推荐复习内容

- FastAPI 官方文档：https://fastapi.tiangolo.com/
- Pydantic 官方文档：https://docs.pydantic.dev/

## 下一节预告

**Section 2: LangChain 核心组件** — Prompt Templates、Output Parsers、LCEL 链式调用
