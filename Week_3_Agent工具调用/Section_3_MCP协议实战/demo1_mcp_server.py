"""
Demo1: MCP Server 创建与工具注册
功能：创建一个简单的 MCP Server → 注册工具 → 通过 stdio 运行
核心：理解 MCP Server 的结构和工具暴露机制
依赖：mcp（已安装）
注意：MCP 1.x 使用 @server.list_tools() 和 @server.call_tool() 注册处理器
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import math
import json
from datetime import datetime
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server 
#stido的音标读法是 /ˈstɪoʊ/，
# 它是 MCP 提供的一种基于标准输入输出的通信方式，
# 适合在本地运行 Server 并通过命令行与 Client 交互。


# ========== 1. 创建 MCP Server ==========
# Server 是 MCP 的核心，负责：
# - 注册工具（告诉 Client 有哪些工具可用）
# - 处理工具调用（Client 调用工具时执行对应逻辑）
# - 通过 stdio 传输与 Client 通信

server = Server("demo-calculator-server") 
# 创建一个 MCP Server 实例，名称为 "demo-calculator-server"，
# 这个名称会在 Client 连接时显示，帮助识别不同的 Server。


# ========== 2. 注册工具列表 ==========
# @server.list_tools() 注册一个处理器，返回 Server 上所有可用工具
# 每个工具用 types.Tool 定义：name、description、inputSchema 
#inputSchema 是 JSON Schema 格式，Client 靠它知道怎么传参

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """返回 Server 暴露的所有工具定义"""
    return [
        types.Tool(
            name="calculator",
            description="计算数学表达式。支持加减乘除、幂运算、开方等。",
            inputSchema={ 
                #inputSchema 定义工具需要的输入参数结构，Client 会根据它构建调用请求
                "type": "object",
                #type 定义输入参数是一个对象，properties 定义对象的属性，
                # 这里只有 expression 一个参数，类型是 string，
                # description 是参数说明，required 定义必填参数列表，
                # 这里 expression 是必填的。
                "properties": {  
                #properties 定义参数列表，这里只有一个参数 expression
                    "expression": {
                        "type": "string", 
                        #参数类型是字符串，Client 调用时需要传入一个字符串表达式
                        "description": "数学表达式，如 '3 + 5 * 2', 'sqrt(144)'"
                    }
                },
                "required": ["expression"]
            }
        ),
        types.Tool(
            name="get_weather",
            description="查询城市天气（模拟数据，实际会调用天气 API）。",
            inputSchema={  
                "type": "object", # JSON Schema 定义输入参数是一个对象
                "properties": { # JSON Schema 定义参数结构
                    "city": { # 参数名 city
                        "type": "string",
                        "description": "城市名称，如 '北京', '上海', '深圳'"
                    }
                },
                "required": ["city"]
            }
        ),
        types.Tool(
            name="get_time",
            description="获取当前日期和时间。",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


# ========== 3. 注册工具调用处理器 ==========
# @server.call_tool() 注册一个处理器，处理 Client 的工具调用请求
# 接收工具名称和参数，返回执行结果

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]: #types.TextContent 定义返回结果的格式，这里是一个文本内容列表
    """处理工具调用请求"""
    if name == "calculator":
        expression = arguments.get("expression", "")
        try:
            allowed = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
            result = eval(expression, {"__builtins__": {}}, allowed)
            return [types.TextContent(type="text", text=str(result))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"计算错误: {e}")]

    elif name == "get_weather":
        city = arguments.get("city", "")
        weather_data = {
            "北京": "晴，25°C，湿度 40%",
            "上海": "多云，22°C，湿度 65%",
            "深圳": "阵雨，28°C，湿度 80%",
        }
        result = weather_data.get(city, f"{city}：暂无天气数据")
        return [types.TextContent(type="text", text=result)]

    elif name == "get_time":
        return [types.TextContent(type="text", text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))]

    else:
        return [types.TextContent(type="text", text=f"未知工具: {name}")]


# ========== 4. 展示 MCP 协议结构 ==========
def show_mcp_protocol():
    """展示 MCP 协议的核心概念"""
    print("=" * 60)
    print("【MCP 协议结构】")
    print("=" * 60)
    print("""
    MCP 通信基于 JSON-RPC 2.0，通过 stdio 传输：

    Client → Server（请求）:
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "calculator",
            "arguments": {"expression": "3 + 5"}
        }
    }

    Server → Client（响应）:
    {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [{"type": "text", "text": "8"}]
        }
    }

    常用 method:
      tools/list          → 列出所有工具
      tools/call          → 调用工具
      resources/list      → 列出资源（文件、数据库等）
      prompts/list        → 列出提示模板
    """)


# ========== 5. 展示工具注册方式 ==========
def show_tool_registration():
    """展示 MCP 1.x 的工具注册方式"""
    print("=" * 60)
    print("【MCP 1.x 工具注册方式】")
    print("=" * 60)
    print("""
    MCP 1.x 使用两个装饰器注册工具：

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        \"\"\"返回工具定义列表\"\"\"
        return [
            types.Tool(
                name="calculator",
                description="计算数学表达式",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"}
                    },
                    "required": ["expression"]
                }
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        \"\"\"处理工具调用\"\"\"
        if name == "calculator":
            result = eval(arguments["expression"])
            return [types.TextContent(type="text", text=str(result))]

    注意：
    - list_tools 返回工具的 schema（name + description + inputSchema）
    - call_tool 接收工具名和参数，返回执行结果
    - inputSchema 是 JSON Schema 格式，Client 靠它知道怎么传参
    """)


# ========== 6. 运行 Server（stdio 传输） ==========
async def run_server():
    """通过 stdio 传输运行 MCP Server"""
    print("=" * 60)
    print("MCP Server 启动中（stdio 模式）...")
    print("=" * 60)
    print("  Server 名称: demo-calculator-server")
    print("  传输方式: stdio（stdin/stdout）")
    print("  工具: calculator, get_weather, get_time")
    print("  等待 Client 连接...")
    print()

    # stdio_server 启动 Server，通过 stdin/stdout 与 Client 通信
    # 这是 MCP 最常用的传输方式
    async with stdio_server() as (read_stream, write_stream): 
        # stdio_server 是 MCP 提供的一个上下文管理器，启动后会返回两个异步流对象：
        # read_stream 用于读取 Client 的请求，write_stream 用于发送响应。
        await server.run(read_stream, write_stream, server.create_initialization_options())
        # server.run() 是 Server 的核心方法，接收读写流和初始化选项，开始处理 Client 请求。
        # 这个方法会一直运行，直到 Server 关闭（如 Ctrl+C）。


# ========== 主函数 ==========
if __name__ == "__main__":
    import asyncio

    # 如果有 --info 参数，展示信息后退出
    if "--info" in sys.argv: # 运行 'python demo1_mcp_server.py --info' 展示 MCP 协议和工具注册方式
        show_mcp_protocol()
        show_tool_registration()
        print("[OK] MCP Server 信息展示完成！")
        print("运行 'python demo1_mcp_server.py' 启动 Server（等待 Client 连接）")
    else:
        # 正常启动 Server
        try:
            asyncio.run(run_server())
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
