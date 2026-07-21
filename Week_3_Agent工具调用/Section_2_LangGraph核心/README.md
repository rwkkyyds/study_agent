# Section 2: LangGraph 核心概念

## 学习目标
1. 理解 LangGraph 的核心思想：用图（Graph）描述 Agent 工作流
2. 掌握 StateGraph 的四大要素：State、Node、Edge、Conditional Edge
3. 用 LangGraph 构建一个完整的 ReAct Agent

## 前置知识
- Section 1: Agent 与 ReAct 框架（@tool 装饰器、推理循环）
- Python TypedDict（类型注解）

## 技术栈
- **框架**: LangGraph 1.2.x
- **LLM**: GLM-4-Flash（智谱 API）
- **模式**: StateGraph（状态图）

## LangGraph 是什么？

```
LangChain Agent（旧）：         LangGraph（新）：
  LLM 自己决定调用什么工具          你用"图"定义工作流
  → 黑盒，难以控制               → 白盒，完全可控
  → 简单场景够用                 → 复杂场景必须用

LangGraph = 把 Agent 的推理过程，显式画成一张有向图
```

## StateGraph 四大要素

```
State（状态）  → 图中流动的数据，类似"全局变量"
Node（节点）   → 处理函数，读取 State → 计算 → 更新 State
Edge（边）     → 节点之间的连线，表示执行顺序
Conditional Edge（条件边）→ 根据 State 内容决定走哪条路
```

```
          ┌─────────┐
          │  START   │
          └────┬─────┘
               │
          ┌────▼─────┐
          │  Node A   │  ← 处理逻辑
          └────┬─────┘
               │
        ┌──────▼──────┐
        │ 条件判断？    │  ← Conditional Edge
        └──┬───────┬───┘
           │       │
     ┌─────▼──┐ ┌──▼─────┐
     │ Node B │ │ Node C  │  ← 不同分支
     └────┬───┘ └──┬──────┘
          │        │
          └───┬────┘
              │
         ┌────▼────┐
         │   END    │
         └─────────┘
```

## 代码结构

### demo1_langgraph_basics.py（图的基础，无 LLM）
1. 用 TypedDict 定义 State
2. 编写 Node 函数
3. 添加普通 Edge 和 Conditional Edge
4. 编译运行图，观察 State 流转

### demo2_langgraph_agent.py（LangGraph ReAct Agent）
1. 定义 Agent State（消息列表）
2. Agent Node（调用 LLM 决策）
3. Tool Node（执行工具）
4. Conditional Edge（判断继续调用工具还是结束）
5. 完整 ReAct 循环

## 运行顺序

```bash
# Step 1: 先理解图的基础概念（无 LLM 调用，纯逻辑）
python demo1_langgraph_basics.py

# Step 2: 用 LangGraph 构建完整 Agent
python demo2_langgraph_agent.py
```

## 注意事项
- demo1 不调用 LLM，纯 Python 逻辑，务必先跑通
- demo2 需要智谱 API Key（环境变量 ZHIPUAI_API_KEY）
- LangGraph 是 2024-2026 年 Agent 工程化的主流框架，面试高频
