# 第 5 周 Section_5：Prometheus 监控

## 本节目标

先用最少依赖理解 Prometheus 指标格式和监控入口：

- Counter：累计请求数、错误数
- Histogram：请求耗时分布
- `/metrics`：给 Prometheus 抓取的文本接口
- FastAPI 中间件：统一统计请求

本节 demo 不强制安装 `prometheus-client`，使用标准库生成 Prometheus text exposition format。掌握概念后再替换为官方客户端库。

## 运行顺序

```powershell
cd "C:\Users\admin\Desktop\AI_Agent_8Weeks_Bootcamp_no_deps_20260720_144614\AI_Agent_8Weeks_Bootcamp\Week_5_监控与部署\Section_5_Prometheus监控"
$py = "..\..\.venv\Scripts\python.exe"
& $py demo1_prometheus_format_basic.py
& $py -m uvicorn demo2_fastapi_metrics:app --host 127.0.0.1 --port 8015
```

打开：

- `http://127.0.0.1:8015/docs`
- `http://127.0.0.1:8015/metrics`

先访问 `/agent/run` 几次，再看 `/metrics` 的数值变化。

## 注意事项

- Counter 只增不减，重启进程后会归零；长期数据由 Prometheus 保存。
- 标签值必须有限且稳定，不能把用户问题、trace ID 当作 label。
- 生产环境应使用 `prometheus-client`，本节手写格式仅用于理解协议。

## 下一步

下一小步将补充业务指标，例如 Agent 成功数、降级次数、Token 使用量。

