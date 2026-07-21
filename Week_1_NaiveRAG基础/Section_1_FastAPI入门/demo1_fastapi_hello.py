"""
Demo 1: FastAPI Hello World
学习目标：理解 FastAPI 最简服务结构
运行方式：python demo1_fastapi_hello.py
访问地址：http://127.0.0.1:8000/docs  (自动生成的Swagger文档)
         http://127.0.0.1:8000/      (根路由)
         http://127.0.0.1:8000/health (健康检查)
"""

from fastapi import FastAPI
import uvicorn

# 创建 FastAPI 应用实例
# 这是整个服务的入口，所有路由都注册在这个对象上
app = FastAPI(
    title="Demo1 FastAPI Hello",
    description="第一个 FastAPI 服务，理解路由基础",
    version="0.1.0",
)


# ========== 路由1：根路径 GET 请求 ==========
# @app.get("/") 是装饰器，表示：当收到 GET / 请求时，执行下面的函数
@app.get("/")
def read_root():
    """最简单的路由，返回一个 JSON 对象"""
    return {"message": "Hello, FastAPI!"}


# ========== 路由2：健康检查 ==========
# 实际项目中，健康检查接口是标配，用于负载均衡器/Docker 探活
@app.get("/health")
def health_check():
    """健康检查接口，返回服务状态"""
    return {"status": "ok"}


# ========== 路由3：路径参数 ==========
# 路径参数：URL 中的变量部分，用 {} 包裹，自动映射到函数参数
@app.get("/items/{item_id}")
def read_item(item_id: int):
    """
    路径参数示例
    - item_id: int 表示 FastAPI 会自动把 URL 中的值转为整数
    - 如果传入非数字，FastAPI 会自动返回 422 错误（Pydantic 校验）
    """
    return {"item_id": item_id, "name": f"商品{item_id}"}


# ========== 路由4：查询参数 ==========
# 查询参数：URL ?key=value 形式的参数
# 当函数参数没有在路径中声明时，FastAPI 自动识别为查询参数
@app.get("/search")
def search_items(
    keyword: str,           # 必填参数
    limit: int = 10,        # 可选参数，默认值 10
    offset: int = 0,        # 可选参数，默认值 0
):
    """
    查询参数示例
    访问：/search?keyword=手机&limit=5&offset=0
    """
    return {
        "keyword": keyword,
        "limit": limit,
        "offset": offset,
        "results": [f"结果{i}" for i in range(offset, offset + limit)],
    }


# ========== 启动入口 ==========
if __name__ == "__main__":
    # uvicorn 是 ASGI 服务器，相当于运行 FastAPI 的"发动机"
    # host="0.0.0.0" 表示监听所有网卡（局域网可访问）
    # port=8000 监听端口
    # reload=True 开发模式下代码修改自动重启
    print("启动 FastAPI 服务...")
    print("Swagger 文档：http://127.0.0.1:8000/docs")
    uvicorn.run("demo1_fastapi_hello:app", host="127.0.0.1", port=8000, reload=True)
