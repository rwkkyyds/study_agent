# 第5周 Section_4：LangSmith 链路追踪与 OpenTelemetry 基础

## 当前小节学习目标

本节先用零新增依赖的方式理解可观测性，再了解 LangSmith 的可选接入方式：

- 理解 trace、span、属性和状态的关系
- 为一次 Agent/RAG 请求记录完整的父子调用链
- 在 FastAPI 中生成请求级 trace id，并记录耗时、输入校验和异常
- 了解 LangSmith 依赖环境变量和 API Key，可按需启用

## 前置知识与学习顺序

已学习 Section_3 JWT 认证、FastAPI 路由和异常处理后，按下面顺序运行：

1. `demo1_otel_span_basic.py`：纯 Python 本地 trace/span 基础
2. `demo2_fastapi_trace.py`：FastAPI 请求链路追踪
3. `demo3_langsmith_optional.py`：LangSmith 可选配置检查，不配置 Key 也能运行

## 代码运行方式

```powershell
cd "C:\Users\admin\Desktop\AI_Agent_8Weeks_Bootcamp_no_deps_20260720_144614\AI_Agent_8Weeks_Bootcamp\Week_5_监控与部署\Section_4_LangSmith与OTel"
$py = "..\..\.venv\Scripts\python.exe"
& $py demo1_otel_span_basic.py
& $py demo3_langsmith_optional.py
& $py -m uvicorn demo2_fastapi_trace:app --host 127.0.0.1 --port 8014
```

打开 `http://127.0.0.1:8014/docs`，调用 `POST /agent/run`。响应中的 `trace_id` 可以关联服务日志和后续指标。

## 注意事项

- 当前 demo 使用标准库生成教学用 trace，目的是先看懂父子 span 和生命周期；生产环境可以替换为 `opentelemetry-api` 与 `opentelemetry-sdk`。
- LangSmith 需要 `LANGCHAIN_API_KEY`，并且会把链路数据发送到外部服务；没有 Key 时 demo 自动进入本地预览模式。
- trace 属性不要写入密码、JWT、身份证号等敏感信息；输入内容也应按脱敏策略处理。

## 推荐复习内容

- trace 与 span 的父子关系
- 请求日志中的 correlation id / trace id
- 记录成功、失败和耗时三个关键维度
- 环境变量配置外部可观测平台

## 下一节学习预告

下一节进入 **Prometheus 监控**，学习如何暴露 QPS、请求耗时、错误数等可抓取指标。
