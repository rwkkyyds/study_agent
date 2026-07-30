# Week 6 Section 1-4 强制阶段测验

**测验时间：** 2026-07-30
**测验范围：** Section 1 LangGraph高级工作流 / Section 2 LangGraph HITL / Section 3 Agent SDK生态 / Section 4 AutoGen/CrewAI对比
**总分：** -/100

---

## 一、选择题（每题 5 分，共 30 分）

### 1. LangGraph 里实现"三个评审节点同时跑，全部完成后汇总"，用的是哪种机制？

- A. 条件边 conditional_edges
- **B. 同一节点指向多个后继节点，再汇聚到一个 merge 节点** ✓
- C. 串行执行三个节点
- D. GroupChat

### 2. 子图（subgraph）和普通函数复用的核心区别是？

- A. 子图不能有状态
- **B. 子图内部有自己的 State，外部图通过状态映射与它交互** ✓
- C. 子图必须用异步
- D. 没有区别

### 3. LangGraph HITL 的 `interrupt` 机制，核心解决什么问题？

- A. 让图跑得更快
- B. 避免节点重复执行
- **C. 在关键节点暂停，等人工审批/编辑后再 resume 继续执行** ✓
- D. 记录日志

### 4. Checkpoint（检查点）配合 `thread_id` 的作用是？

- A. 加速向量检索
- **B. 隔离不同用户/会话的状态，并支持中断后恢复** ✓
- C. 限制并发数
- D. 加密通信

### 5. Agent SDK 生态里，PydanticAI 相比裸调 OpenAI 的核心价值是？

- A. 自动联网搜索
- **B. 用 Pydantic 模型对 Agent 输出做强类型结构化约束** ✓
- C. 免费调用模型
- D. 替代 LangChain

### 6. AutoGen 和 CrewAI 的本质区别，下面哪个说法最准？

- A. AutoGen 性能更好
- B. CrewAI 只支持两个 Agent
- **C. AutoGen 靠 Agent 间对话推进，CrewAI 靠任务依赖串成流水线推进** ✓
- D. 两者完全一样

---

## 二、简答题（每题 10 分，共 40 分）

### 7. 画出 LangGraph 条件路由工单分流的结构图，说明为什么用条件边而不是串行（10/10）

**答案要点：**
用户工单 → classify 节点（判断类型）→ 条件边 route_ticket：
- 类型=支付 → handle_payment
- 类型=技术 → handle_tech
- 类型=复杂 → handle_human

为什么不用串行：因为三类工单互斥，不需要每个工单都过三个处理节点；条件边让图只走匹配的那条分支，省掉无关节点执行。

### 8. 解释 interrupt + resume 的完整生命周期（10/10）

**答案要点：**
1. 图执行到 `interrupt` 节点时暂停，当前状态被 Checkpoint 存盘
2. 暂停期间可以把中间状态暴露给人审批或编辑
3. 人操作后，用 `Command(resume=...)` 把人工结果注入状态
4. 图从暂停点继续执行后续节点，而不是从头跑

关键点：interrupt 不结束图，resume 不重启图，是"暂停-注入-继续"。

### 9. 对比 AutoGen 的 speaker_selection_strategy 和 CrewAI 的 context_from，各自解决什么问题？（10/10）

**答案要点：**
- AutoGen 的 speaker_selection：解决"多 Agent 在一个会话里，下一句该轮到谁说话"。auto 模式让 LLM 根据上下文选，round_robin 按顺序轮流，manual 人工指定。控制的是对话的发言权流转。
- CrewAI 的 context_from：解决"任务之间的数据依赖"。声明前置任务 id，Crew 据此做拓扑排序，上一个任务产出喂给下一个。控制的是任务流水线的执行顺序和数据交接。

一个管"谁说话"，一个管"谁先干、数据怎么传"。

### 10. 教学大纲标注 Section 4「压缩1天，了解即可」，本节用轻量 dataclass 模拟而不是装真实框架，这样做的理由是什么？（10/10）

**答案要点：**
1. 大纲定位是了解思想、做选型判断，不是精通 API
2. 真实 AutoGen/CrewAI 依赖重、要 LLM API Key 才能跑，会卡在环境配置而非学思想
3. 用 dataclass 把"对话驱动"和"任务驱动"的编排骨架抽出来，差异一目了然
4. 以后真要做选型，对照这里的思路读官方文档会更快

---

## 三、代码题（每题 15 分，共 30 分）

### 11. 写出 LangGraph 条件路由的核心：route 函数（15/15）

根据 ticket 的 category 返回不同的节点名。

```python
def route_ticket(state: TicketState) -> str:
    category = state["category"]
    if category == "payment":
        return "handle_payment"
    elif category == "tech":
        return "handle_tech"
    else:
        return "handle_human"
```

**配套建图（关键几行）：**
```python
graph = StateGraph(TicketState)
graph.add_node("classify", classify_ticket)
graph.add_node("handle_payment", handle_payment)
graph.add_node("handle_tech", handle_tech)
graph.add_node("handle_human", handle_human)
graph.add_edge(START, "classify")
graph.add_conditional_edges("classify", route_ticket, {
    "handle_payment": "handle_payment",
    "handle_tech": "handle_tech",
    "handle_human": "handle_human",
})
```

### 12. 写出 CrewAI 轻量实现里 Task 依赖驱动的 kickoff 核心逻辑（15/15）

```python
def kickoff(self, goal: str) -> str:
    by_name = {a.name: a for a in self.agents}
    outputs: dict[str, str] = {"__goal__": goal}
    for task in self.tasks:
        # 拼接前置任务的产出作为上下文
        context = "\n".join(outputs.get(dep, "") for dep in task.context_from)
        agent = by_name[task.agent_name]
        result = agent.execute(task.description, context)
        outputs[task.id] = result
    return outputs[self.tasks[-1].id]
```

---

## 自评表（做完后填写）

| 题型 | 得分 | 满分 |
|------|------|------|
| 选择题 | - | 30 |
| 简答题 | - | 40 |
| 代码题 | - | 30 |
| **总计** | **-** | **100** |

**需要补强的点（答不上来的记这里）：**

> 📋 **使用说明：**
> 1. 先不要看下面的知识点清单，独立做完这 12 题
> 2. 做完后对照 memory.md 章节内容自查
> 3. 把自评得分填进表格，回复得分
> 4. 低于 70 分建议复习对应 Section 再进入 Section 5
