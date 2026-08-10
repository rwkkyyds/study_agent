# 03 — Docker Compose 编排

> 相关文件：`docker-compose.yml`

## 一、Docker Compose 的作用

Docker Compose 将多个服务组合为一个运行环境：

```yaml
services:
  app:        # FastAPI 应用
  postgres:   # 数据库
  redis:      # 缓存与共享状态
```

执行 `docker compose up --build -d` 后，所有服务同时启动，彼此通过服务名通信。

## 二、服务定义

### 1. 应用服务

```yaml
app:
  build:
    context: .
    dockerfile: Dockerfile
  ports:
    - "8000:8000"
  environment:
    - DATABASE_URL=postgresql://rag_user:rag_password@postgres:5432/rag_db
    - REDIS_URL=redis://redis:6379/0
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_started
```

- `build` 指定构建上下文和 Dockerfile 路径。
- `ports` 将容器内 8000 端口映射到宿主机 8000 端口。
- `environment` 设置环境变量，覆盖默认值。
- `depends_on` 确保 PostgreSQL 健康检查通过后应用才启动。

### 2. PostgreSQL 服务

```yaml
postgres:
  image: postgres:16-alpine
  environment:
    - POSTGRES_USER=rag_user
    - POSTGRES_PASSWORD=rag_password
    - POSTGRES_DB=rag_db
  volumes:
    - postgres-data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U rag_user -d rag_db"]
```

- `postgres:16-alpine` 镜像体积小，适合生产。
- 通过环境变量创建数据库用户和库。
- 持久卷确保容器重启后数据不丢失。
- `pg_isready` 检测数据库是否就绪。

### 3. Redis 服务

```yaml
redis:
  image: redis:7-alpine
  volumes:
    - redis-data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
```

- `redis:7-alpine` 轻量级 Redis 镜像。
- 持久卷保存 Redis 数据。
- `redis-cli ping` 检测 Redis 是否就绪。

### 4. Milvus 服务（可选）

```yaml
# milvus:
#   image: milvusdb/milvus:latest
#   depends_on:
#     - etcd
#     - minio
```

Milvus 需要 etcd 和 MinIO 两个额外依赖，资源占用较大，默认注释。按需启用即可。

## 三、数据持久化

```yaml
volumes:
  postgres-data:
    name: rag-postgres-data
  redis-data:
    name: rag-redis-data
```

- 命名卷（named volumes）由 Docker 管理，存储在 `/var/lib/docker/volumes/`。
- 容器删除后卷仍然存在，数据不会丢失。
- 使用 `docker compose down -v` 删除卷。

## 四、网络隔离

```yaml
networks:
  rag-network:
    name: rag-network
    driver: bridge
```

- 所有服务在同一个 `rag-network` 网络中。
- 服务之间通过服务名通信（例如 `postgres:5432`）。
- 外部无法直接访问容器内部，只有 `ports` 暴露的端口可达。

## 五、启动和停止

```powershell
# 构建并启动所有服务
docker compose up --build -d

# 查看启动日志
docker compose logs -f

# 查看所有服务状态
docker compose ps

# 停止所有服务，保留数据
docker compose down

# 停止所有服务，删除数据卷
docker compose down -v
```

## 六、生产环境配置

生产部署时，建议创建 `.env` 文件覆盖敏感配置：

```text
# .env
JWT_SECRET_KEY=<生成一个至少 32 字节的随机字符串>
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
SESSION_TTL_SECONDS=3600
SESSION_MAX_MESSAGES=20
```

然后在 `docker-compose.yml` 中引用：

```yaml
app:
  environment:
    - JWT_SECRET_KEY=${JWT_SECRET_KEY}
```

## 七、注意事项

- **首次启动时**，PostgreSQL 需要初始化数据库，应用可能在 10-20 秒后才可访问。
- **日志**：生产环境建议配置日志收集，避免日志填满磁盘。
- **资源限制**：可通过 `deploy.resources` 限制每个服务的 CPU 和内存使用。
- **安全**：`rag_password` 是示例密码，生产环境应使用强密码，并通过 `.env` 文件注入。