"""企业级智能客服 RAG 系统 — 生产级 Dockerfile。

构建策略：多阶段构建，分离依赖安装和运行时，最小化最终镜像体积。
"""

# ============================================================
# 阶段一：依赖安装
# ============================================================
FROM python:3.10-slim AS builder

WORKDIR /build

# 系统依赖：仅安装编译所需的最小工具
RUN apt-get update && \
    apt-get install --no-install-recommends -y gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 先复制依赖清单，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================================
# 阶段二：运行镜像
# ============================================================
FROM python:3.10-slim

# 运行时只需要 libpq（psycopg2 二进制包不需要 gcc）
RUN apt-get update && \
    apt-get install --no-install-recommends -y libpq5 && \
    rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制已安装的包
COPY --from=builder /root/.local /root/.local

# 确保 pip 安装的本地包在 PATH 中
ENV PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 复制应用代码
COPY app/ ./app/

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 暴露 API 端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]