# Section 3: MCP 协议实战

## 学习目标
1. 理解 MCP（Model Context Protocol）协议的核心思想
2. 掌握 MCP Server 的创建（暴露工具给 LLM）
3. 掌握 MCP Client 的使用（连接 Server、发现工具、调用工具）
4. 将 MCP 工具集成到 LangGraph Agent

## 前置知识
- Section 1: @tool 装饰器、Agent 推理循环
- Section 2: LangGraph StateGraph、Node、Edge

## 技术栈
- **协议**: MCP (Model Context Protocol) 1.x
- **库**: mcp, langchain-mcp-adapters
- **传输**: stdio（标准输入输出，最常用的传输方式）

## MCP 是什么？

```
传统方式：                      MCP 方式：
  工具写在代码里                   工具作为独立服务运行
  → 每个框架一套接口               → 统一协议，任何框架都能用
  → 换框架要重写                   → 写一次，到处用

MCP = 工具领域的 USB-C
  USB-C 统一了充电/数据/视频接口
  MCP 统一了 LLM ↔ 工具的通信接口
```

## MCP 架构

```
┌─────────────┐     MCP 协议      ┌─────────────┐
│  MCP Client  │ ←─── stdio ────→ │  MCP Server  │
│  (你的代码)   │     JSON-RPC     │  (工具服务)   │
└──────┬──────┘                   └──────┬──────┘
       │                                 │
       ▼                                 ▼
  LangGraph Agent                  具体工具实现
  (决定调用什么工具)                 (执行文件读写/API调用等)
```

## MCP 三大内置 Server

| Server | 用途 | 工具示例 |
|--------|------|----------|
| Filesystem | 文件系统操作 | read_file, write_file, list_directory |
| GitHub | GitHub API | create_issue, search_repos, get_file |
| Playwright | 浏览器自动化 | navigate, click, screenshot |

## 代码结构

### demo1_mcp_server.py（MCP Server 入门）
1. 创建一个简单的 MCP Server
2. 注册工具（用 @server.tool 装饰器）
3. 通过 stdio 传输运行 Server
4. 测试工具调用

### demo2_mcp_langgraph.py（MCP + LangGraph 集成）
1. 用 MCP Client 连接 Server
2. 发现 Server 暴露的工具
3. 将 MCP 工具转换为 LangChain Tool
4. 在 LangGraph Agent 中使用 MCP 工具

## 运行顺序

```bash
# Step 1: 理解 MCP Server 的创建（独立进程）
python demo1_mcp_server.py

# Step 2: MCP + LangGraph 集成（Client 连接 Server）
python demo2_mcp_langgraph.py
```

## 注意事项
- MCP Server 是独立进程，通过 stdio（stdin/stdout）与 Client 通信
- 通信格式是 JSON-RPC 2.0
- Filesystem/GitHub/Playwright Server 需要额外安装，本节用自定义 Server 演示原理
