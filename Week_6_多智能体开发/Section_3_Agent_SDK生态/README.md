# Week 6 Section 3: Agent SDK 生态

## 这一节到底学什么

这一节不是让你背某一个框架的 API。

你要学的是：**不同 Agent SDK 到底在帮开发者解决什么问题。**

可以先记一句话：

```text
Agent SDK = 把模型、工具、结构化输出、运行流程、监控和安全边界包装成一套开发方式。
```

你以后会看到很多 SDK：

- OpenAI Agents SDK
- PydanticAI
- LangGraph / LangGraph SDK
- MCP
- CrewAI / AutoGen

它们名字不同，但核心问题差不多：

```text
怎么定义 Agent？
怎么注册工具？
怎么让模型调用工具？
怎么约束输出格式？
怎么记录运行过程？
怎么接入外部工具生态？
```

## 本节学习顺序

1. `demo1_sdk_common_runtime.py`
   - 不绑定具体 SDK
   - 先看所有 Agent SDK 的共同骨架
   - Agent、Tool、Runner、Result 分别是什么

2. `demo2_pydantic_ai_structured_output.py`
   - 使用真实 `pydantic-ai`
   - 重点看结构化输出和类型约束
   - 不需要 API Key，使用 SDK 自带测试模型

3. `demo3_openai_agents_tool_shape.py`
   - 使用真实 `openai-agents`
   - 重点看 Agent 和 tool 的定义方式
   - 不调用远程模型，避免卡在 API Key

## 为什么这一节不直接上真实大模型

因为本节目标是学 SDK 生态，不是测模型能力。

如果一开始就接真实大模型，你会被这些问题打断：

```text
API Key
网络
费用
模型输出不稳定
不同厂商参数差异
```

所以本节先把 SDK 的开发形态跑通。

等你理解了：

```text
Agent 怎么定义
Tool 怎么注册
Result 怎么约束
Runner 怎么执行
```

再接真实模型会顺很多。

## 开发里什么时候用 Agent SDK

当你只是写一个简单 prompt，不一定需要 Agent SDK。

但如果你开始需要这些能力，就该考虑 SDK：

```text
多个工具
结构化输出
多步骤执行
输入/输出校验
日志追踪
安全边界
多 Agent 协作
MCP 工具接入
```

## 本节一句话

```text
不要先站队框架，先看它解决的问题。
```

