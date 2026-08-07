# 06 - 认证 API

> 对应文件：`app/api/auth.py`

路由前缀是 `/auth`，标签是 `auth`，所以完整路径为：

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

## 一、注册：POST /auth/register

请求：

```json
{
  "username": "alice",
  "password": "secret123",
  "role": "customer"
}
```

规则：

- 用户名长度 3–50。
- 密码长度 6–100。
- 角色只能是 `admin`、`agent`、`customer`。

成功响应：`201 Created`

```json
{
  "id": 1,
  "username": "alice",
  "role": "customer",
  "is_active": true,
  "created_at": "2026-08-04T02:00:00"
}
```

不会返回 `hashed_password`。

## 二、登录：POST /auth/login

请求：

```json
{
  "username": "alice",
  "password": "secret123"
}
```

成功响应：`200 OK`

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer"
}
```

错误密码和不存在用户都返回 `401`。

## 三、当前用户：GET /auth/me

请求头：

```text
Authorization: Bearer <登录返回的 access_token>
```

成功响应是 `UserResponse`。缺少凭证、Token 无效、用户不存在或账号禁用时返回 `401`。

## 四、在 Swagger 中验证

1. 启动：`uvicorn app.main:app --reload`
2. 打开：`http://127.0.0.1:8000/docs`
3. 执行 `POST /auth/register`。
4. 执行 `POST /auth/login`，复制 `access_token`。
5. 在 Swagger 右上角 `Authorize` 中输入 `Bearer <token>`。
6. 执行 `GET /auth/me`。

## 五、路由层为什么很薄

路由只做四件事：

1. 接收 Pydantic Schema。
2. 通过 `Depends(get_db)` 获取数据库。
3. 调用 `services/auth.py`。
4. 交给 `response_model` 序列化结果。

这样可以避免把密码、JWT 和数据库操作逻辑全部堆在一个路由文件中。