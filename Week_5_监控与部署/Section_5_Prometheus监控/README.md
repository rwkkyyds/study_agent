# 第5周 Section_5：Prometheus 监控与指标暴露

## 当前小节学习目标

本节学习如何让服务把“运行状态”暴露出来，方便 Prometheus 采集。

你需要先跑通下面这条链路：

```text
FastAPI 服务运行
  -> 记录请求次数、错误次数、耗时、业务数值
  -> 暴露 /metrics 接口
  -> Prometheus 读取指标文本
  -> 后续 Grafana 展示图表
```

学完本节你应该能做到：

- 理解 Counter、Gauge、Histogram 三类常见指标
- 看懂 Prometheus 文本格式
- 用 FastAPI 暴露 `/metrics`
- 用 middleware 统计请求总数、状态码、接口耗时
- 在没有 `prometheus_client` 包时也能先跑通核心逻辑

## 前置知识与学习顺序

建议按顺序运行：

1. `demo1_metrics_plain_text.py`
   - 重点：Prometheus 文本格式、Counter、Gauge
2. `demo2_fastapi_metrics_middleware.py`
   - 重点：FastAPI middleware、请求次数、状态码、耗时桶
3. `demo3_prometheus_client_real.py`
   - 重点：`prometheus_client` 真实标准写法

## 代码运行方式

进入当前目录：

```powershell
cd "D:\agent_study_doc\AI_Agent_8Weeks_Bootcamp\Week_5_监控与部署\Section_5_Prometheus监控"
```

运行无依赖指标格式 demo：

```powershell
python demo1_metrics_plain_text.py
```

运行 FastAPI 指标中间件 demo：

```powershell
python demo2_fastapi_metrics_middleware.py
```

运行 Prometheus 客户端真实 demo：

```powershell
python demo3_prometheus_client_real.py
```

也可以启动 FastAPI 服务：

```powershell
uvicorn demo2_fastapi_metrics_middleware:app --reload --port 8000
```

访问指标接口：

```text
http://127.0.0.1:8000/metrics
```

## 注意事项

- Counter 只能增加，适合请求总数、错误总数。
- Gauge 可增可减，适合当前在线用户数、队列长度、内存占用。
- Histogram 用分桶统计耗时，适合接口延迟、LLM 调用耗时。
- Prometheus 是主动拉取 `/metrics`，不是应用主动推送。
- 本节使用真实 `prometheus-client` 包生成标准指标文本。
- 本节不引入 Grafana 大盘，下一节再讲可视化。

## 推荐复习内容

- FastAPI middleware
- HTTP 状态码
- QPS、错误率、P95/P99 延迟
- 上一节 OpenTelemetry 中 trace 与本节 metrics 的区别

## 下一节学习预告

下一节进入 **Grafana 监控大盘可视化搭建**，重点学习把 Prometheus 指标变成可读图表。
