"""
Demo 2: Pydantic 数据校验 + POST 请求 + 异步 I/O
学习目标：掌握请求体校验、POST 路由、async/await 基础
运行方式：python demo2_fastapi_param.py
访问地址：http://127.0.0.1:8001/docs
"""

from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import asyncio
import time

app = FastAPI(title="Demo2 Pydantic + 异步", version="0.1.0")


# ========== Pydantic 模型定义 ==========
# Pydantic 模型 = 数据校验 + 自动文档生成的利器
# 只要继承 BaseModel，FastAPI 就能自动校验请求体、生成 Swagger 文档

class ItemCreate(BaseModel):
    """创建商品的请求体模型"""
    name: str = Field(..., min_length=1, max_length=50, description="商品名称")
    price: float = Field(..., gt=0, description="商品价格，必须大于0")
    description: Optional[str] = Field(None, max_length=500, description="商品描述（可选）")
    in_stock: bool = Field(True, description="是否有库存，默认True")


class ItemResponse(BaseModel):
    """返回给前端的响应模型（可以和请求体不同）"""
    id: int
    name: str
    price: float
    description: str
    in_stock: bool


# 模拟数据库（内存字典）
fake_db: dict[int, dict] = {}
next_id: int = 1


# ========== POST 请求：创建商品 ==========
@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate):
    """
    POST 请求接收 JSON 请求体
    - item: ItemCreate -> FastAPI 自动解析 JSON 并用 Pydantic 校验
    - 如果校验失败（如 price=-1），自动返回 422 错误
    - status_code=201 表示"创建成功"
    """
    global next_id
    item_id = next_id
    next_id += 1

    # 存入模拟数据库
    record = {
        "id": item_id,
        "name": item.name,
        "price": item.price,
        "description": item.description or "暂无描述",
        "in_stock": item.in_stock,
    }
    fake_db[item_id] = record

    return record


# ========== GET 请求：查询单个商品 ==========
@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(
    item_id: int = Path(..., description="商品ID"),
):
    """
    路径参数用 Path 声明，可以加元数据（description等）
    """
    if item_id not in fake_db:
        # 手动抛出 HTTP 异常，FastAPI 会转为对应的 HTTP 响应
        raise HTTPException(status_code=404, detail=f"商品 {item_id} 不存在")

    return fake_db[item_id]


# ========== GET 请求：商品列表（查询参数高级用法） ==========
@app.get("/items")
def list_items(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    min_price: float = Query(0, ge=0, description="最低价格"),
    max_price: float = Query(999999, le=999999, description="最高价格"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
):
    """
    Query 声明查询参数，可设置默认值、范围限制、描述
    """
    results = list(fake_db.values())

    # 过滤逻辑
    if keyword:
        results = [r for r in results if keyword in r["name"]]
    results = [r for r in results if min_price <= r["price"] <= max_price]

    return {"total": len(results), "items": results[:limit]}


# ========== PUT 请求：更新商品 ==========
@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item: ItemCreate):
    """
    PUT 用于全量更新
    """
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail=f"商品 {item_id} 不存在")

    record = {
        "id": item_id,
        "name": item.name,
        "price": item.price,
        "description": item.description or "暂无描述",
        "in_stock": item.in_stock,
    }
    fake_db[item_id] = record
    return record


# ========== DELETE 请求 ==========
@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    """
    DELETE 删除资源，204 表示无内容返回
    """
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail=f"商品 {item_id} 不存在")

    del fake_db[item_id]
    return None


# ========== 异步 I/O 演示 ==========
# 关键概念：同步 vs 异步
# 同步：一个请求处理完才能处理下一个（排队）
# 异步：遇到 IO 等待时，CPU 去处理其他请求（并发）

@app.get("/sync-demo")
def sync_slow_endpoint():
    """同步版本：sleep 期间，整个服务被阻塞"""
    time.sleep(2)  # 模拟 2 秒的 IO 操作（如数据库查询）
    return {"mode": "sync", "message": "我阻塞了整个服务 2 秒"}


@app.get("/async-demo")
async def async_slow_endpoint():
    """
    异步版本：await 期间，CPU 可以去处理其他请求
    - async def 声明这是异步函数
    - await 告诉程序"这里要等，先去忙别的"
    - asyncio.sleep 替代 time.sleep（不阻塞事件循环）
    """
    await asyncio.sleep(2)  # 异步等待，不阻塞其他请求
    return {"mode": "async", "message": "我等待了 2 秒，但没阻塞别人"}


# ========== 异步 vs 同步对比接口 ==========
@app.get("/compare")
async def compare():
    """
    对比演示：
    访问 /sync-demo 连续刷新两次 -> 总共等 4 秒（串行）
    访问 /async-demo 连续刷新两次 -> 总共等 2 秒（并发）
    """
    return {
        "tip": "同时请求 /sync-demo 两次 和 /async-demo 两次，感受区别",
        "sync": "time.sleep(2) 阻塞整个服务",
        "async": "await asyncio.sleep(2) 不阻塞其他请求",
    }


if __name__ == "__main__":
    print("启动 Demo2 服务...")
    print("Swagger 文档：http://127.0.0.1:8001/docs")
    uvicorn.run("demo2_fastapi_param:app", host="127.0.0.1", port=8001, reload=True)
