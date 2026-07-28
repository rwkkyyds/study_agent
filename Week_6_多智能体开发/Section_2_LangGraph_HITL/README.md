# Week 6 Section 2: LangGraph HITL

## 这一节到底学什么

HITL 是 Human-in-the-loop，意思是：**人在关键节点参与流程**。

你可以把它理解成：

```text
Agent 不是所有事情都自己拍板。
遇到高风险动作时，先暂停，等人确认，再继续执行。
```

这在真实项目里非常重要。

比如：

- Agent 要删除数据：必须先问人
- Agent 要发邮件：必须先让人确认内容
- Agent 要退款：必须先让客服确认
- Agent 要执行部署：必须先让开发确认
- Agent 对用户投诉给出赔偿方案：必须先让人工审核

## 本节学习顺序

1. `demo1_interrupt_approval_basic.py`
   - 最小 HITL 示例
   - 流程暂停，等待人工批准
   - 批准后继续执行

2. `demo2_refund_approval_workflow.py`
   - 模拟客服退款审批
   - 小额退款自动通过
   - 大额退款需要人工确认

3. `demo3_edit_before_send.py`
   - 模拟 Agent 写好回复后，人工编辑再发送
   - 不是只有批准/拒绝，也可以修改内容

## 运行方式

进入目录：

```powershell
cd "D:\agent_study_doc\AI_Agent_8Weeks_Bootcamp\Week_6_多智能体开发\Section_2_LangGraph_HITL"
```

依次运行：

```powershell
python demo1_interrupt_approval_basic.py
python demo2_refund_approval_workflow.py
python demo3_edit_before_send.py
```

## 你要抓住的核心

HITL 的核心不是“让程序 input 一下”。

真正核心是：

```text
流程可以暂停
状态可以保存
人给出决定
流程可以从暂停点继续
```

LangGraph 里靠这几个东西实现：

```text
interrupt()      暂停流程，抛出等待人工输入的请求
MemorySaver      保存流程状态
Command(resume=) 带着人的决定继续流程
thread_id        标识同一条流程
```

## 开发里什么时候用

只要 Agent 要做“可能造成真实后果”的动作，就应该考虑 HITL。

常见场景：

```text
发邮件前确认
删数据前确认
退款前确认
执行部署前确认
调用付费 API 前确认
给客户最终回复前审核
```

## 本节一句话

```text
HITL 是给 Agent 加刹车：高风险动作先停下来，让人确认后再继续。
```

