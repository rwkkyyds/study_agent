# 02 — Dockerfile 与镜像构建

> 相关文件：`Dockerfile`、`.dockerignore`

## 一、为什么选择多阶段构建

单阶段 Dockerfile 的问题：

```dockerfile
# 单阶段：所有内容都在一个层
FROM python:3.10-slim
COPY requirements.txt .
RUN pip install -r requirements.txt    # 安装依赖
COPY app/ ./app/                        # 复制代码
```

这样构建的镜像体积较大，因为：

- 依赖安装工具（pip、gcc、Python 头文件）保留在最终镜像中。
- 包缓存文件保留在镜像中。
- 不需要的文档和测试代码也打包进镜像。

阶段六使用多阶段构建：

```text
阶段一（builder）：安装依赖，编译需要 gcc 的包
阶段二（runtime）：只复制已安装的包和代码，不携带编译工具
```

## 二、阶段一：依赖安装

```dockerfile
FROM python:3.10-slim AS builder
WORKDIR /build

# 安装编译所需的最小系统工具
RUN apt-get update && \
    apt-get install --no-install-recommends -y gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
```

关键点：

- `--no-cache-dir` 避免 pip 缓存增大镜像。
- `--user` 安装到用户目录，方便后续复制。
- `--no-install-recommends` 只安装编译所需的最小系统包。
- 最后删除 apt 缓存，减少层体积。

## 三、阶段二：运行镜像

```dockerfile
FROM python:3.10-slim

# 运行时只需要 libpq（psycopg2 二进制包不需要 gcc）
RUN apt-get update && \
    apt-get install --no-install-recommends -y libpq5 && \
    rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制已安装的包
COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 只复制应用代码，不复制文档和测试
COPY app/ ./app/

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; ..." || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

关键点：

- `libpq5` 是 PostgreSQL 客户端运行时库，不需要编译工具。
- `PYTHONDONTWRITEBYTECODE=1` 不生成 `__pycache__`。
- `PYTHONUNBUFFERED=1` 日志实时输出。
- `WORKDIR /app` 设置工作目录，所有路径相对于 `/app`。
- `HEALTHCHECK` 定期检查 `/health` 接口。
- 使用 `--workers 2` 启动两个 worker，平衡并发和资源消耗。

## 四、.dockerignore 排除的文件

`.dockerignore` 的作用是告诉 Docker 构建上下文要排除哪些文件，避免：

- 将 `.venv`、`__pycache__`、`*.db` 等本地文件打包进镜像。
- 将 `docs/` 和 `tests/` 等运行时不需要的目录打包进镜像。
- 将 `.git` 目录打包进镜像。

```text
.git
__pycache__/
*.pyc
.pytest_cache/
.venv/
*.db
.env
.env.local
docs/
tests/
*.md
```

## 五、构建验证

```powershell
# 构建镜像
docker build -t enterprise-customer-service-rag:latest .

# 查看镜像大小
docker images enterprise-customer-service-rag

# 运行容器
docker run -d --name rag-app-test -p 8000:8000 `
  -e DATABASE_URL=sqlite:///./rag_dev.db `
  -e JWT_SECRET_KEY=test-secret-key `
  enterprise-customer-service-rag:latest

# 验证健康检查
curl http://localhost:8000/health

# 清理
docker stop rag-app-test && docker rm rag-app-test
```

## 六、构建优化要点

- **利用缓存层**：`requirements.txt` 单独复制和安装，只要依赖不变，这一层就不会重新构建。
- **最小化层数**：将多个 `RUN` 命令合并，减少镜像层数。
- **移除包管理器缓存**：apt 和 pip 的缓存不会在运行时使用，安装后立即删除。
- **只复制运行时需要的文件**：不复制文档、测试、本地配置和版本控制文件。