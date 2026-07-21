# 第5周 Section_3：OAuth2.0 / JWT 认证与 FastAPI 安全中间件

## 当前小节学习目标

本节只学习后端认证链路，不进入 React 前端。

你需要跑通下面这条生产常见链路：

```text
用户名密码登录 -> 后端校验密码 -> 签发 JWT -> 请求携带 Bearer Token -> 后端解析 Token -> 访问受保护接口
```

学完本节你应该能做到：

- 用 FastAPI 实现 `/login` 登录接口
- 使用 bcrypt 存储和校验密码哈希
- 使用 PyJWT 签发和验证访问令牌
- 使用 `OAuth2PasswordBearer` 保护接口
- 用角色字段实现基础权限控制

## 前置知识与学习顺序

建议按顺序运行：

1. `demo1_jwt_login_basic.py`
   - 重点：密码哈希、登录校验、JWT 签发
2. `demo2_security_dependency.py`
   - 重点：FastAPI 安全依赖、Bearer Token、当前用户解析
3. `demo3_role_permission.py`
   - 重点：角色权限、管理员接口、权限不足处理

## 代码运行方式

进入当前目录：

```powershell
cd "D:\agent_study_doc\AI_Agent_8Weeks_Bootcamp\Week_5_监控与部署\Section_3_JWT认证"
```

运行第一个 demo：

```powershell
python demo1_jwt_login_basic.py
```

或启动 FastAPI 服务：

```powershell
uvicorn demo2_security_dependency:app --reload --port 8000
```

打开接口文档：

```text
http://127.0.0.1:8000/docs
```

测试账号：

```text
普通用户：admin 密码：admin123 角色：admin
普通用户：alice 密码：alice123 角色：user
```

## 注意事项

- JWT 里的 `SECRET_KEY` 在生产环境必须来自环境变量，不能硬编码在代码里。
- JWT 只适合存放用户ID、角色、过期时间等少量非敏感信息，不要放密码、手机号、身份证等敏感信息。
- 密码不能明文存储，必须存储哈希值。
- Token 过期时间不能无限长，生产环境还需要配合刷新令牌、黑名单或版本号机制。

## 推荐复习内容

- FastAPI 依赖注入 `Depends`
- Pydantic 请求体校验
- HTTP 401 与 403 的区别
- JWT 三段结构：Header、Payload、Signature

## 下一节学习预告

下一节进入 **LangSmith 链路追踪与 OpenTelemetry 可观测性基础**，重点学习如何记录一次 Agent/RAG 请求的完整执行链路。

