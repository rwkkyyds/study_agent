# Section 1: Agent 核心概念与 ReAct 框架

## 学习目标
1. 理解 Agent 的本质：LLM + Tools + 推理循环
2. 掌握 ReAct 框架：Reasoning（思考）+ Acting（行动）
3. 用 LangChain 构建第一个可运行的 Agent

## 前置知识
- Week 1-2 的 LangChain LCEL 链路
- Prompt Template、Output Parser

## 技术栈
- **框架**: LangChain Agent（langchain 1.3.x create_agent API）
- **LLM**: GLM-4-Flash（智谱 API）
- **工具**: 自定义 @tool 装饰器
- **模式**: ReAct（思考 → 行动 → 观察 → 循环）

## Agent 是什么？

```
传统 LLM：用户问题 → LLM → 回答（一次调用，无工具）

Agent：用户问题 → LLM 思考 → 调用工具 → 观察结果 → 继续思考 → ... → 最终回答
       ↑_________________________循环_________________________↑
```

Agent = LLM（大脑） + Tools（手脚） + 推理循环（工作流）

## ReAct 框架

ReAct = **Re**asoning + **Act**ing

```
用户问题: "计算 3+5 等于多少？"
    ↓
Thought: 用户问的是数学计算，我应该用 calculator 工具
Action:  calculator("3 + 5")
Observation: "8"
Thought: 工具返回了结果 8，我可以直接回答了
Answer:  3 + 5 = 8
```

## 代码结构

### demo1_tool_basics.py（工具定义基础）
1. @tool 装饰器的原理和用法
2. 工具属性查看（name、description、args_schema）
3. 工具直接调用测试（不经过 Agent）
4. docstring 对 Agent 决策的影响

### demo2_react_agent.py（ReAct Agent 完整推理循环）
1. 定义多个工具（计算器、知识库、时间查询）
2. 用 create_agent 创建 ReAct Agent
3. 运行推理循环，展示 Thought → Action → Observation
4. 测试单工具和多工具组合问题

## 运行顺序

```bash
# Step 1: 先理解工具定义
python demo1_tool_basics.py

# Step 2: 再运行完整 Agent
python demo2_react_agent.py
```

## 注意事项
- 本节无额外依赖，Week 1-2 的环境即可运行
- Agent 推理过程会有多轮 LLM 调用，比 RAG 慢
- 工具调用是 Agent 的核心能力，下一节会深入讲工具开发
