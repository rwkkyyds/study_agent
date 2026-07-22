# AI Agent 8 Weeks Bootcamp

这是一个面向 AI Agent 工程化落地的 8 周学习项目，覆盖 FastAPI、LangChain、RAG、Agent、数据库、性能优化、认证、监控与部署等核心内容。

项目采用“先跑通代码，再理解原理，最后复盘沉淀”的学习方式。每个小节都尽量提供可独立运行的 demo、学习笔记和面试复盘材料。

## 学习路线

| 阶段 | 主题 | 主要内容 |
| --- | --- | --- |
| 第 1 周 | Naive RAG 基础 | FastAPI、LangChain、文档分块、Embedding、端到端 RAG |
| 第 2 周 | Advanced RAG | Query Transformation、混合检索、RAG 评估、Milvus、复杂文档解析 |
| 第 3 周 | Agent 与 Tool Calling | ReAct、LangGraph、MCP、PostgreSQL、Memory、异常处理 |
| 第 4 周 | 性能优化与数据层 | Redis、PostgreSQL 进阶、pgvector、异步并发、Celery、压测 |
| 第 5 周 | 认证、监控与部署 | JWT、OpenTelemetry、LangSmith、Prometheus、Grafana、Docker |
| 第 6 周 | 多智能体系统 | 高级 LangGraph、Human-in-the-Loop、Agent SDK、多 Agent 架构 |
| 第 7-8 周 | 工业级项目实战 | 企业级客服 RAG、AI 面试官系统、部署与简历面试冲刺 |

## 目录结构

```text
AI_Agent_8Weeks_Bootcamp/
├── Script/
├── Week_1_NaiveRAG基础/
├── Week_2_AdvancedRAG/
├── Week_3_Agent工具调用/
├── Week_4_性能优化与数据层/
├── Week_5_监控与部署/
├── learning_plan.md
├── progress.md
├── memory.md
├── requirements.txt
└── README.md
```

## 运行方式

优先使用项目自带虚拟环境：

```powershell
cd "C:\Users\admin\Desktop\AI_Agent_8Weeks_Bootcamp_no_deps_20260720_144614\AI_Agent_8Weeks_Bootcamp"
.\.venv\Scripts\python.exe --version
```

运行某个小节 demo 时，进入对应目录后执行：

```powershell
..\..\.venv\Scripts\python.exe demo文件名.py
```

FastAPI 示例通常可以这样启动：

```powershell
..\..\.venv\Scripts\python.exe -m uvicorn demo文件名:app --host 127.0.0.1 --port 8000
```

## 环境变量

仓库不会提交真实 API Key。需要调用真实模型时，请在本地设置环境变量：

```powershell
$env:ZHIPU_API_KEY="你的智谱API Key"
$env:GLM_API_KEY="你的GLM API Key"
$env:DEEPSEEK_API_KEY="你的DeepSeek API Key"
```

`.env`、`.venv`、日志文件和缓存目录已通过 `.gitignore` 排除。

## 当前进度

最新学习进度记录在 `progress.md`。当前已推进到第 5 周监控与部署部分，正在学习 Prometheus 监控。

## 学习建议

1. 每次只学习一个小节。
2. 先运行 demo，再看 README 和学习笔记。
3. 遇到不理解的地方，记录到对应小节的 `不理解的部分.md`。
4. 完成小节后再看 `生产级高频面试题.md` 做复盘。

