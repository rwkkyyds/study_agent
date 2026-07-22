# 第5周 Section_4：LangSmith 链路追踪与 OpenTelemetry 可观测性基础

## 当前小节学习目标

本节学习如何观察一次 AI 应用请求的完整执行链路。

你需要先跑通下面这条链路：

```text
用户请求 -> 业务函数 -> LLM/Agent/RAG 子步骤 -> 生成 trace/span -> 本地或平台查看执行过程
```

学完本节你应该能做到：

- 理解 trace、span、attribute、event 的基本含义
- 用 LangSmith 给 LLM/Agent 调用加链路追踪
- 用 OpenTelemetry 手动创建 span
- 给 FastAPI 请求增加最小可观测性
- 在没有在线 API Key 时也能本地运行 demo

## 前置知识与学习顺序

建议按顺序运行：

1. `demo1_langsmith_trace.py`
   - 重点：LangSmith `@traceable`、父子调用链、无 API Key 本地运行
2. `demo2_otel_manual_span.py`
   - 重点：OpenTelemetry span、attribute、event、异常记录
3. `demo3_fastapi_otel.py`
   - 重点：FastAPI 中间件、请求级 trace、HTTP 状态记录

## 代码运行方式

进入当前目录：

```powershell
cd "D:\agent_study_doc\AI_Agent_8Weeks_Bootcamp\Week_5_监控与部署\Section_4_LangSmith与OTel"
```

运行 LangSmith demo：

```powershell
python demo1_langsmith_trace.py
```

运行 OpenTelemetry 手动 span demo：

```powershell
python demo2_otel_manual_span.py
```

运行 FastAPI 请求追踪 demo：

```powershell
python demo3_fastapi_otel.py
```

也可以启动 FastAPI 服务：

```powershell
uvicorn demo3_fastapi_otel:app --reload --port 8000
```

打开接口文档：

```text
http://127.0.0.1:8000/docs
```

## 可选环境变量

LangSmith 在线追踪需要配置：

```powershell
$env:LANGSMITH_TRACING="true"
$env:LANGSMITH_API_KEY="你的 LangSmith API Key"
$env:LANGSMITH_PROJECT="ai-agent-bootcamp"
```

如果没有配置 API Key，`demo1_langsmith_trace.py` 会关闭在线上报，只保留本地执行输出。

## 注意事项

- LangSmith 更偏向 LLM/Agent/RAG 链路追踪，适合看 Prompt、输入输出和工具调用过程。
- OpenTelemetry 是通用可观测性标准，适合服务请求、数据库、队列、外部 HTTP 调用等系统链路。
- 本节 demo 不强依赖在线服务，缺少 OpenTelemetry 包时会降级为本地输出，保证先跑通学习链路。
- 生产环境通常会把 trace 发送到 Jaeger、Tempo、Grafana、Datadog、OTel Collector 等系统。

## 推荐复习内容

- FastAPI 中间件
- try-except 异常捕获
- HTTP 请求状态码
- Agent/RAG 中一次请求会拆成哪些子步骤

## 下一节学习预告

下一节进入 **Prometheus 监控与业务/系统指标暴露**，重点学习 QPS、错误数、延迟直方图等指标。

