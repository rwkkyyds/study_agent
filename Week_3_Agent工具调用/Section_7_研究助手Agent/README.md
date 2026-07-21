# Section 7: 搭建 RAG + 联网搜索研究助手 Agent

## 学习目标
1. 综合运用 Week3 所学：Agent + Tool Calling + Memory + 异常处理
2. 构建一个能联网搜索 + 知识库检索 + 数据库查询的研究助手
3. 掌握多工具协作的 Agent 工作流设计

## 前置知识
- Section 1: Agent 与 ReAct 框架
- Section 2: LangGraph StateGraph、条件路由
- Section 3: MCP 协议（工具注册思想）
- Section 5: Agent Memory（会话持久化）
- Section 6: 异常处理与降级

## 技术栈
- **框架**: LangGraph 1.x
- **工具**: 自定义 @tool（搜索/检索/SQL）
- **存储**: 内存 FAISS（知识库）+ SQLite（数据库）
- **记忆**: MemorySaver（会话记忆）

## 研究助手能力

```
用户提问
  │
  ├─ "最近AI Agent有什么进展？"  → 联网搜索工具
  ├─ "RAG的原理是什么？"         → 知识库检索工具
  ├─ "数据库里有多少用户？"       → SQL查询工具
  └─ "对比一下Milvus和FAISS"     → 搜索 + 检索 组合
```

## 代码结构

### demo1_search_agent.py（联网搜索 Agent）
1. 定义搜索工具（模拟/真实 API）
2. 构建 ReAct Agent（LLM 自主决定调用哪个工具）
3. 搜索结果整合与回答

### demo2_rag_agent.py（知识库检索 Agent）
1. 构建小型 FAISS 知识库
2. 定义检索工具
3. RAG Agent 工作流

### demo3_research_assistant.py（完整研究助手）
1. 多工具注册（搜索 + 检索 + SQL）
2. Agent 自主选择工具
3. 会话记忆 + 异常处理
4. 完整研究助手工作流

## 运行顺序

```bash
# Step 1: 联网搜索 Agent
python demo1_search_agent.py

# Step 2: 知识库检索 Agent
python demo2_rag_agent.py

# Step 3: 完整研究助手（综合所有工具）
python demo3_research_assistant.py
```

## 注意事项
- demo1 使用模拟搜索，无需真实 API Key
- demo2 使用本地 FAISS，无需外部向量库
- demo3 综合所有工具，是 Week3 的最终 Demo
- 所有 demo 均包含异常处理和日志
