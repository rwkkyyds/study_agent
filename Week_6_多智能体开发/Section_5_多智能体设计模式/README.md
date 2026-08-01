# Week 6 Section 5: 多智能体设计模式、异常处理与容错

## 这一节到底学什么

前四节你学了单个 Agent 怎么定义、多 Agent 怎么编排。
但真正上线的多智能体系统，还要回答两个工程问题：

```text
1. 多个 Agent 怎么组织协作？用哪种结构？   ← 设计模式
2. 某个 Agent 挂了/超时了/输出垃圾怎么办？  ← 容错
```

这一节把这两个问题一起讲，并产出第6周的周 Demo。

## 本节核心：三种经典设计模式

| 模式 | 结构 | 谁适合 | 典型场景 |
|------|------|--------|----------|
| 分层（Hierarchical） | 有 manager 统筹，向下分发 | 流程可拆、有明确指挥 | 客服分级、订单处理 |
| 对等（Peer-to-Peer） | 无中心，Agent 互相调用 | 需要讨论/协商 | 方案评审、头脑风暴 |
| 流水线（Pipeline） | 串行传递，上游产出喂下游 | 流程清晰、步骤固定 | 调研→写作→审核发布 |

一句话类比：

```text
分层 = 公司有部门经理，经理派活给组员
对等 = 几个专家圆桌讨论，谁有信息谁发言
流水线 = 工厂流水线，上一道工序的半成品交给下一道
```

## 本节学习顺序

1. `demo1_design_patterns.py`
   - 用轻量实现演示三种设计模式的结构差异
   - 同一个目标分别用三种模式跑一遍
   - 看清每种模式的控制流

2. `demo2_resilient_multiagent.py`
   - 多智能体系统的容错：超时/重试/降级/熔断
   - 一个 Agent 挂了不能拖垮整个系统
   - 结合第3周 Section_6 的异常处理思想，搬到多 Agent 场景

3. `demo3_week6_demo.py`
   - 第6周综合 Demo
   - 整合：LangGraph 工作流 + HITL + 多 Agent 协作 + 容错
   - 场景：智能客服工单处理系统
     - 分类 Agent → 路由到不同处理 Agent
     - 高风险工单 interrupt 等人审
     - 处理失败自动重试 + 降级

## 为什么这一节是周 Demo 收尾

第6周目标是"多智能体协作系统"，这一节把前四节串起来：

```text
Section 1 LangGraph 高级工作流 → 提供流程控制底座
Section 2 HITL                 → 提供人工审批能力
Section 3 Agent SDK 生态       → 提供单 Agent 定义方式
Section 4 AutoGen/CrewAI       → 提供多 Agent 编排思路
Section 5 设计模式 + 容错      → 组装成可上线的多智能体系统
```

## 运行方式

```powershell
cd "c:\Users\admin\Desktop\agent_study\Week_6_多智能体开发\Section_5_多智能体设计模式"
python demo1_design_patterns.py
python demo2_resilient_multiagent.py
python demo3_week6_demo.py
```

三个 demo 都是零依赖（纯标准库 + dataclass），不需要 API Key，不需要 Docker。

## 本节你只需要记住

```text
设计模式不是选一个用到底，而是根据业务环节特性组合。
容错的本质是：单个 Agent 的故障不能传染给整个系统。
```

## 下一步

先把三个 demo 跑通。

跑通后再生成：
- 学习笔记
- 生产级高频面试题
- 不理解的部分
