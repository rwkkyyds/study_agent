# Week 5 Section 6: Grafana 监控大盘

## 这一节到底学什么

上一节 Prometheus 解决的是：服务把指标暴露出来，Prometheus 定时抓走。

这一节 Grafana 解决的是：把 Prometheus 里的数字变成图，让人一眼看懂系统现在健不健康。

你可以这样理解：

```text
FastAPI 服务
  -> 暴露 /metrics
  -> Prometheus 抓指标
  -> Grafana 连 Prometheus
  -> Grafana 画出请求量、错误量、接口耗时
```

Grafana 本身不负责采集指标，它更像一个“监控看板”。真正存指标的是 Prometheus。

## 开发里什么时候会用到

当你的服务上线后，别人问这些问题时，就需要 Grafana：

- 今天接口请求量是不是突然涨了？
- 用户说系统慢，到底是不是接口变慢了？
- 500 错误是不是变多了？
- `/chat` 接口 P95 耗时是多少？
- 发布新版本后，服务有没有异常？

如果没有 Grafana，你只能翻日志、看终端、猜问题。

有了 Grafana，你可以直接看图：

```text
请求量上升了吗？
错误率升高了吗？
接口耗时变慢了吗？
```

## 本节文件说明

建议按这个顺序看：

1. `demo1_fastapi_metrics_app.py`
   - 一个真实 FastAPI 服务
   - 暴露 `/health`、`/chat`、`/boom`、`/metrics`
   - 使用真实 `prometheus_client`

2. `demo2_load_generator.py`
   - 自动请求 FastAPI 服务
   - 用来制造请求量和错误量
   - 否则 Grafana 图表会很空

3. `prometheus.yml`
   - 告诉 Prometheus 去抓哪个服务的 `/metrics`

4. `docker-compose.yml`
   - 一键启动 Prometheus + Grafana

5. `grafana/dashboards/fastapi-overview.json`
   - Grafana 自动导入的大盘

## 运行方式

先进入本节目录：

```powershell
cd "D:\agent_study_doc\AI_Agent_8Weeks_Bootcamp\Week_5_监控与部署\Section_6_Grafana大盘"
```

### 第一步：启动 FastAPI 指标服务

```powershell
uvicorn demo1_fastapi_metrics_app:app --reload --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000/metrics
```

如果能看到一堆 `demo_` 开头的指标，说明服务指标暴露成功。

### 第二步：启动 Prometheus 和 Grafana

另开一个终端，在同一个目录执行：

```powershell
docker compose up -d
```

打开 Prometheus：

```text
http://127.0.0.1:9090
```

打开 Grafana：

```text
http://127.0.0.1:3000
```

默认账号密码：

```text
admin / admin
```

登录后进入 Dashboards，可以看到 `FastAPI Prometheus Overview`。

### 第三步：制造一些请求

再开一个终端执行：

```powershell
python demo2_load_generator.py
```

这时候 Grafana 的图会开始有变化。

## 你重点看什么

不要一开始陷进 Grafana 的各种菜单里。

先只看这三个问题：

```text
1. 请求量有没有变？
2. 错误数有没有变？
3. 请求耗时有没有变？
```

对应到大盘里就是：

- Requests by status
- 5xx errors
- P95 request duration

## 常用 PromQL

请求量：

```promql
sum by (path, status) (rate(demo_http_requests_total[1m]))
```

5xx 错误量：

```promql
sum by (path) (rate(demo_http_requests_total{status=~"5.."}[1m]))
```

P95 接口耗时：

```promql
histogram_quantile(0.95, sum by (le, path) (rate(demo_http_request_duration_seconds_bucket[1m])))
```

当前活跃用户：

```promql
demo_active_users
```

## 本节你只需要记住

Grafana 不是用来写业务代码的。

Grafana 是你服务上线后，用来看“系统现在到底怎么样”的。

开发者学习 Grafana 的目的不是成为运维，而是上线后你能回答：

```text
我的服务有没有挂？
哪里慢？
哪里错？
是不是刚发版导致的？
```

## 下一步

先把本节跑通。

跑通后再生成：

- 学习笔记
- 生产级高频面试题
- 不理解的部分

