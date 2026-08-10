# 阶段六：容器化与部署

> 将前五个阶段的应用打包为 Docker 镜像，使用 Docker Compose 编排应用、PostgreSQL、Redis，完成从"本地可运行"到"容器化可部署"的转变。

## 文档索引

| 文件 | 内容 |
|------|------|
| [01-容器化概述](01-容器化概述.md) | 阶段六架构、目标、与阶段五的区别 |
| [02-Dockerfile与镜像构建](02-Dockerfile与镜像构建.md) | 多阶段构建、Dockerfile 每一层的作用 |
| [03-DockerCompose编排](03-DockerCompose编排.md) | 服务定义、依赖、数据持久化、网络隔离 |
| [04-部署环境与运维](04-部署环境与运维.md) | 部署准备、日志、备份、升级、安全 |
| [05-项目总结与后续规划](05-项目总结与后续规划.md) | 六个阶段技术演进回顾、后续规划 |

## 相关文件

| 文件 | 作用 |
|------|------|
| `Dockerfile` | 多阶段构建，生产级镜像 |
| `.dockerignore` | 排除本地文件，最小化构建上下文 |
| `docker-compose.yml` | 编排 App + PostgreSQL + Redis |

## 快速启动

```powershell
# 构建并启动所有服务
docker compose up --build -d

# 验证健康检查
curl http://localhost:8000/health

# 查看日志
docker compose logs -f app

# 停止所有服务
docker compose down
```

## 完成标准

- `docker compose up --build -d` 后所有服务正常启动。
- `GET /health` 返回 `{"status": "ok"}`。
- 容器重启后数据不丢失。
- 阶段一到阶段五全部功能在容器内正常运行。