# 04 - 密码哈希与 JWT

对应文件：`app/services/auth.py`

## 一、密码哈希

注册流程：

```text
用户明文密码
    │
    ▼
hash_password()
    │
    ▼
PBKDF2-SHA256 哈希字符串
    │
    ▼
写入 User.hashed_password
```

登录流程不会重新计算并比较两个明文，而是调用：

```text
verify_password(用户输入的明文, 数据库中的哈希)
```

密码安全规则：

- 不把明文密码写入数据库。
- 不把密码写入日志。
- 不把 `hashed_password` 放入 `UserResponse`。
- 生产环境应通过环境变量设置足够长度的 JWT 密钥。

## 二、JWT 的内容

本项目使用 `PyJWT`，算法来自配置：

- `jwt_algorithm`：默认 `HS256`
- `jwt_secret_key`：默认开发占位值，生产必须替换
- `jwt_expire_minutes`：默认 60 分钟

Token 的 payload 至少包含：

| 字段 | 含义 |
|------|------|
| `sub` | 用户 id；PyJWT 要求以字符串保存 |
| `exp` | 过期时间 |

`create_access_token()` 会把非字符串的 `sub` 转成字符串；`get_current_user()` 解析后再转回整数查询数据库。

## 三、Token 生命周期

```text
登录成功
  │
  ▼
服务端签发 JWT
  │
  ▼
客户端保存 Token
  │
  ▼
请求头：Authorization: Bearer <token>
  │
  ▼
HTTPBearer 提取凭证
  │
  ▼
jwt.decode 校验签名和 exp
  │
  ▼
查询 users 表
  │
  ├── 用户不存在/禁用 → 401
  └── 用户有效 → 继续访问
```

## 四、为什么仅有 Token 还不够

Token 通过签名只能证明它由服务端签发，并不能保证用户现在仍然有效。用户可能已经被禁用，所以每次访问受保护接口仍然要查询数据库，并检查 `is_active`。

## 五、常见错误

| 错误 | 原因 | 处理 |
|------|------|------|
| `Subject must be a string` | `sub` 使用整数写入 JWT | 签发前转字符串 |
| `无效的 Token` | 签名错误、过期或格式错误 | 重新登录获取 Token |
| `用户不存在或已禁用` | Token 合法但用户状态无效 | 检查数据库账号状态 |
| `InsecureKeyLengthWarning` | 开发默认密钥过短 | 在 `.env` 设置至少 32 字节随机密钥 |

## 六、开发环境配置

`.env.example` 只提供配置格式，不放真实密钥：

```text
JWT_SECRET_KEY=replace-with-a-long-random-secret
```

真实密钥禁止提交到 Git。