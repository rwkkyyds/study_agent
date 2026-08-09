# 阶段二：身份认证与数据层

> 在阶段一项目骨架上，先建立“谁在访问系统”和“业务数据如何保存”这两条基础能力。

## 一、为什么阶段一之后先做认证和数据层

阶段一的服务虽然能够启动并返回健康状态，但它还没有真实业务身份：任何请求都无法区分用户，也没有用户、知识库文档、工单和消息这些业务实体。

如果先写客服逻辑，再补认证，容易出现两个问题：

1. 业务函数接收客户端传来的 `customer_id`，用户可以伪造身份。
2. 工单和消息没有明确的外键关系，后续很难做权限校验和数据审计。

因此本阶段先把身份边界和数据边界固定下来。阶段三的知识库检索、阶段四的转人工工单，都建立在这里的模型和 JWT 依赖之上。

## 二、本阶段架构

```text
客户端
  │
  ├── POST /auth/register ──→ 注册 API ──→ Auth Service ──→ User ──→ SQLite
  │
  ├── POST /auth/login ─────→ 登录 API ──→ 校验密码 ──→ JWT
  │
  └── GET /auth/me ─────────→ HTTPBearer ──→ 解析 JWT ──→ 查询 User ──→ 响应

业务数据：
User ──< Ticket ──< Message
User ──< Document ──< Chunk
```

## 三、文件之间如何协作

1. `app/models/` 定义数据库表和外键关系。
2. `app/schemas/auth.py` 定义注册、登录和响应的数据形状。
3. `app/services/auth.py` 负责密码哈希、用户查询、JWT 签发和角色校验。
4. `app/api/auth.py` 只处理 HTTP 参数和依赖注入，不把认证细节全部堆在路由中。
5. `app/main.py` 注册认证路由，并在生命周期中初始化数据库。
6. `tests/test_auth.py` 为每个测试创建独立数据库，验证成功、失败和边界场景。

## 四、核心安全边界

- 数据库只保存密码哈希，不保存明文密码。
- JWT 的 `sub` 保存用户 ID，接口仍然要回数据库确认用户存在且启用。
- `admin` 可以访问管理员能力，`agent` 和 `customer` 不能越权。
- 后续阶段获取客户身份必须使用 `get_current_user` 的结果，不能信任请求体里的用户 ID。

## 五、本阶段交付物

- User、Document、Chunk、Ticket、Message 五个模型。
- 注册、登录、当前用户接口。
- PBKDF2-SHA256 密码哈希。
- JWT 签发、解析、过期和用户状态校验。
- `require_role()` 角色依赖工厂。
- 认证专项测试和全量回归测试。

## 六、运行验证

```powershell
.venv\Scripts\python.exe -m pytest tests/test_auth.py -v
.venv\Scripts\python.exe -m pytest tests/ -v
```

完成标准：注册、登录、Token 校验、无效 Token、重复用户名和角色权限测试均通过。

## 七、当前不实现

- PostgreSQL 生产迁移和 Alembic。
- OAuth2、SSO 和第三方登录。
- 文档上传和向量入库。
- Redis Session 和请求限流。
- 管理后台页面。

这些能力分别在后续阶段展开。

## 八、文档索引

| 文档 | 内容 |
|------|------|
| [01-阶段二概述](01-阶段二概述.md) | 本阶段目标、链路和安全边界 |
| [02-用户模型](02-用户模型.md) | User 字段、角色和账号状态 |
| [03-知识库与工单模型](03-知识库与工单模型.md) | Document、Chunk、Ticket、Message |
| [04-密码哈希与 JWT](04-密码哈希与JWT.md) | 密码和 Token 生命周期 |
| [05-认证服务](05-认证服务.md) | 认证函数和业务职责 |
| [06-认证 API](06-认证API.md) | 注册、登录、当前用户接口 |
| [07-角色权限与依赖注入](07-角色权限与依赖注入.md) | Depends 和角色边界 |
| [08-接口测试与排错](08-接口测试与排错.md) | 测试隔离、命令和常见问题 |
