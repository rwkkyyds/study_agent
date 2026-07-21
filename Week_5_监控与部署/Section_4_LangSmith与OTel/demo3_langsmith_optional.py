"""LangSmith 可选接入检查：无 langsmith 或 API Key 时仍可本地运行。"""

from __future__ import annotations

import os
import uuid


def langsmith_status() -> dict[str, str | bool]:
    """只检查配置，不发起网络请求，避免无意中上传学习数据。"""

    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    try:
        import langsmith  # type: ignore  # 可选依赖：未安装时走本地模式
    except ImportError:
        return {"enabled": False, "mode": "local", "reason": "未安装 langsmith"}
    if not api_key:
        return {"enabled": False, "mode": "local", "reason": "未设置 LANGCHAIN_API_KEY"}
    return {"enabled": True, "mode": "langsmith", "client": langsmith.__name__}


def build_run_preview(question: str) -> dict[str, str | dict[str, str | bool]]:
    """生成一次链路预览；真正发送 LangSmith 需在业务代码中显式创建 Client。"""

    return {"run_id": str(uuid.uuid4()), "name": "agent.run", "inputs": question, "status": langsmith_status()}


if __name__ == "__main__":
    print(build_run_preview("如何给 Agent 增加链路追踪？"))
