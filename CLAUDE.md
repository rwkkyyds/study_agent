# CLAUDE.md - AI Agent 8 Weeks Bootcamp

## 项目概述

8周 AI Agent 工程化落地全流程学习项目，从零构建 RAG + Agent + 多智能体系统。

## 当前进度

- **当前阶段：** 第5周 - 前端、认证、监控与部署
- **下一节：** Section_1_React前端基础
- **已完成：** Week1全部(6节) + Week2全部(6节) + Week3全部(7节) + Week4全部(7节)，共26节

## 目录结构

```
AI_Agent_8Weeks_Bootcamp/
├── Week_1_NaiveRAG基础/    # 6个Section，已完成
├── Week_2_AdvancedRAG/     # 6个Section，已完成
├── Week_3_Agent工具调用/    # 7个Section
├── Week_4_性能优化与数据层/  # 7个Section
├── Week_5_前端认证监控部署/  # 7个Section
├── Week_6_多智能体与高级Agent/ # 5个Section
├── Week_7_8_工业级项目/     # 2个全栈项目+系统设计+面试
├── Script/                 # 测验文件
├── learning_plan.md        # 每日学习计划
├── progress.md             # 学习进度跟踪
└── memory.md               # 教学大纲与规则
```

## 教学规则（摘要）

1. **一次一小节**，禁止一次性生成整章内容
2. **分步输出**：先出 README.md + demo.py，运行成功后再出学习笔记/面试题
3. **每3小节强制测验**：代码实战 + 知识查漏
4. **代码规范**：零报错可运行、详尽注释、强制 try-except/logging/Pydantic
5. **教学顺序**：先跑通代码 → 再讲原理 → 再复盘输出
6. **用现成组件**：默认调用组件而非手写轮子，除非用户明确要求底层实现
7. **答疑记录**：用户说"看不懂/报错/不理解"时，通俗解释+类比+示例代码，可记录到《不理解的部分.md》

## 每小节文件规范

每个Section目录包含：
- `README.md` - 学习目标、运行方式、注意事项
- `demo*.py` - 可运行的示例代码
- `学习笔记.md` - 知识点整理
- `生产级高频面试题.md` - 面试准备
- `不理解的部分.md` - 疑问记录

## 快捷指令

- **继续** → 进入下一节
- **答疑** → 解决当前疑惑
- **复习** → 生成小节复习题

## 技术栈

- Python 3.10+, FastAPI, LangChain, FAISS, Chroma, Milvus
- Docker, Docker Compose
- Redis, Prometheus, Grafana, LangSmith
- AutoGen, CrewAI (Week 6)
