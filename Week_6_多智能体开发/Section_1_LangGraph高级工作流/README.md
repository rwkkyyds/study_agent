# Week 6 Section 1: LangGraph 高级工作流

## 这一节到底学什么

前面你已经见过 LangGraph 的基础用法：

```text
节点 Node
边 Edge
状态 State
条件路由 Conditional Edge
```

这一节进入高级一点的用法，但不要把它想复杂。

你可以把 LangGraph 理解成：**给 Agent 做流程编排的工具**。

普通 Agent 像一个人自己想、自己做。

LangGraph 高级工作流更像一个小团队：

```text
有人负责分析
有人负责执行
有人负责检查
有人负责汇总
```

你作为开发，学这一节是为了以后能做这种系统：

- 客服 Agent：先判断问题类型，再走不同处理流程
- RAG Agent：先检索，再判断资料够不够，不够就补查
- 代码助手：先分析需求，再写代码，再自检
- 多工具 Agent：根据任务类型选择不同工具链
- 多智能体系统：不同角色各做一部分，最后汇总

## 本节学习顺序

1. `demo1_parallel_review_workflow.py`
   - 学并行分工
   - 一个任务同时交给多个角色处理
   - 最后汇总结果

2. `demo2_conditional_ticket_router.py`
   - 学条件路由
   - 不同问题走不同处理节点
   - 像真实客服系统分流

3. `demo3_subgraph_order_pipeline.py`
   - 学子图 subgraph
   - 把一小段流程封装成一个可复用模块
   - 大项目里避免主图越来越乱

## 运行方式

进入本节目录：

```powershell
cd "D:\agent_study_doc\AI_Agent_8Weeks_Bootcamp\Week_6_多智能体开发\Section_1_LangGraph高级工作流"
```

依次运行：

```powershell
python demo1_parallel_review_workflow.py
python demo2_conditional_ticket_router.py
python demo3_subgraph_order_pipeline.py
```

## 你要重点理解的不是语法

这节先别纠结 LangGraph 每个 API 的底层实现。

你先抓住三个开发场景：

```text
并行：一个任务，多个角色同时看
路由：不同输入，走不同处理路线
子图：一段复杂流程，封装起来复用
```

## 本节和真实开发有什么关系

真实 AI Agent 项目不是“一问一答”这么简单。

上线后的 Agent 通常要做这些事：

```text
判断任务类型
选择工具
调用检索
调用模型
检查结果
失败重试
人工确认
汇总输出
```

如果全部写成一堆 if-else，项目很快会乱。

LangGraph 的价值就是：把这些流程画成清晰的图，让你知道每一步在哪里、下一步去哪里。

## 下一节预告

下一节进入：

```text
Section_2_LangGraph HITL
```

也就是 Human-in-the-loop：让人在关键节点参与确认。

