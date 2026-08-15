# 生产级替换方案总览

> 本文档整理了本项目从「开发原型」到「生产级」的**关键替换方案**，涵盖配置管理、数据层、RAG 引擎、认证、工作流、稳定性、容器化部署和前端等 8 大领域共 14 项替换。每个方案均体现了「接口化设计 + 可插拔适配器 + 自动回退」的核心思想。

---

## 目录

| 领域 | 替换方案 | 状态 |
|------|----------|------|
| **一、配置管理** | 1. 环境变量集中管理 | ✅ 已完成 |
| **二、数据层** | 2. 数据库会话管理 (SQLite ↔ PostgreSQL) | ✅ 已完成 |
| **三、RAG 引擎** | 3. Embedding 实现 (Mock ↔ DashScope) | ✅ 已完成 |
| | 4. 向量存储 (InMemory ↔ Milvus) | ✅ 已完成 |
| | 5. LLM 回答生成 (QwenLLM) | ✅ 已完成 |
| | 6. 检索编排 (Retriever) | ✅ 已完成 |
| | 7. 文档切分器 (TextChunker) | ✅ 已完成 |
| **四、认证层** | 8. JWT 认证与角色权限 | ✅ 已完成 |
| **五、工单系统** | 9. 工单与消息模型 | ✅ 已完成 |
| **六、工作流** | 10. LangGraph 客服工作流 | ✅ 已完成 |
| **七、稳定性** | 11. 重试/熔断/降级 | ✅ 已完成 |
| | 12. 滑动窗口限流 | ✅ 已完成 |
| | 13. Prometheus 指标 | ✅ 已完成 |
| **八、部署** | 14. Docker 多阶段构建与编排 | ✅ 已完成 |

---

## 一、配置管理

### 1. 环境变量集中管理

**目标：** 将密钥、数据库连接、开关等配置项从业务代码中剥离，集中管理。

**替换方式：**

| 开发原型 | 生产级方案 |
|----------|------------|
| `os.getenv("DASHSCOPE_API_KEY")` 散落在各处 | `pydantic-settings` + `BaseSettings` 统一加载 |
| 硬编码密钥（如 `jwt_secret_key = "change-me"`） | `.env` 文件驱动，生产环境强制校验密钥强度 |

**核心文件：** `app/core/config.py`

```python
class Settings(BaseSettings):
    database_url: str = "sqlite:///./rag_dev.db"          # 开发默认 SQLite
    dashscope_api_key: str | None = None                  # 生产环境设置
    jwt_secret_key: str = "change-me-in-env"              # 生产强制变更
    environment: str = "development"                      # 区分环境

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v, info):
        if info.data.get("environment") == "production":
            if v == "change-me-in-env":
                raise ValueError("生产环境必须设置 JWT_SECRET_KEY")
            if len(v.encode("utf-8")) < 32:
                raise ValueError("密钥长度不足 32 字符")
        return v
```

**关键设计点：**
- `@lru_cache` 缓存配置单例，避免重复解析
- `SettingsConfigDict(env_file=".env")` 自动加载 `.env` 文件
- `extra="ignore"` 兼容多余环境变量
- 生产环境 `field_validator` 在启动时即阻断错误配置

---

## 二、数据层

### 2. 数据库会话管理 (SQLite ↔ PostgreSQL)

**目标：** 开发环境零配置运行 SQLite，生产环境无感切换到 PostgreSQL。

**替换方式：**

| 开发原型 | 生产级方案 |
|----------|------------|
| 直接 `sqlite3.connect()` | `SQLAlchemy` + `sessionmaker` 工厂 |
| 手动创建表 | `Base.metadata.create_all()` + 预留 Alembic |
| 无会话管理 | `get_db()` 依赖注入，请求级生命周期 |

**核心文件：** `app/db/session.py`

```python
DATABASE_URL = settings.database_url  # 来自环境变量
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**切换方式：** 只需修改 `.env` 中的 `DATABASE_URL`：
```
# 开发
DATABASE_URL=sqlite:///./rag_dev.db

# 生产
DATABASE_URL=postgresql://rag_user:rag_password@host:5432/rag_db
```

**模型设计：**
- `User` — 多角色（admin/agent/customer），PBKDF2 哈希密码
- `Document` / `Chunk` — 知识库文档与切分块，JSON 元数据
- `Ticket` / `Message` — 工单系统，状态 + 优先级 + 消息记录

---

## 三、RAG 引擎

### 3. Embedding 实现 (Mock ↔ DashScope)

**目标：** 本地开发使用确定性 Mock Embedding，生产环境调用通义千问 text-embedding-v3。

**替换方式：**

| 开发原型 | 生产级方案 |
|----------|------------|
| 简单随机向量 | `MockEmbedding`：SHA256 稳定映射 + L2 归一化 |
| 硬编码 API 调用 | `DashScopeEmbedding`：接口一致，可互换 |
| 无法测试 | Mock 确定性输出，支持单元测试断言 |

**核心文件：** `app/rag/embeddings.py`

```
                 ┌──────────────────────┐
                 │    Retriever 使用     │
                 │  (不关心具体实现)       │
                 └───────┬──────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
     ┌─────────────────┐  ┌─────────────────┐
     │  MockEmbedding   │  │ DashScopeEmbedding│
     │  (本地确定性)      │  │ (通义千问 API)     │
     │  dimension=768   │  │ dimension=1024    │
     └─────────────────┘  └─────────────────┘
```

**自动回退逻辑**（`retriever.py` 中的工厂函数）：
```python
def _default_embedding():
    if os.environ.get("DASHSCOPE_API_KEY"):
        try:
            return DashScopeEmbedding()
        except Exception:
            pass
    return MockEmbedding()
```

### 4. 向量存储 (InMemory ↔ Milvus)

**目标：** 本地开发使用进程内内存向量库，生产环境切换到 Milvus 分布式向量数据库。

**替换方式：**

| 开发原型 | 生产级方案 |
|----------|------------|
| 列表 + 循环比对 | `InMemoryVectorStore`：余弦相似度 + Top-K |
| 无持久化 | `MilvusVectorStore`：IVF_FLAT 索引 + 内积度量 |
| 单机不可扩展 | Milvus：分布式、可扩展、支持 GPU |

**核心文件：** `app/rag/vector_store.py`

```
┌─────────────────────────────────────┐
│          VectorRecord                │
│  (id, vector, text, metadata)       │
└─────────────────────────────────────┘
                ▲
                │ upsert / search / count
                │
      ┌─────────┴──────────┐
      ▼                    ▼
┌──────────────┐   ┌──────────────┐
│InMemoryVector │   │MilvusVector  │
│Store          │   │Store         │
│(本地测试)       │   │(生产分布式)    │
└──────────────┘   └──────────────┘
```

**接口一致：** 两个实现都提供 `upsert()`、`search()`、`count()` 方法，`Retriever` 在构造时注入即可切换。

### 5. LLM 回答生成 (QwenLLM)

**目标：** 封装 DashScope Generation API，提供专业的客服 RAG 回答生成。

**核心文件：** `app/rag/llm.py`

**关键设计点：**
- 系统提示词（SYSTEM_PROMPT）定义客服角色行为边界
- `_build_messages()` 构建完整消息链：系统提示 → 历史 → 上下文 → 用户问题
- `result_format="message"` 使用 DashScope 消息格式
- `count_tokens()` 中文按 1.5 字/ token、英文按 4 字/ token 估算

```python
class QwenLLM:
    def generate(self, query, context="", history=None):
        messages = self._build_messages(query, context, history or [])
        return self._call_api(messages)
    
    def _build_messages(self, query, context, history):
        # 系统提示 → 对话历史 → 知识库上下文 + 用户问题
```

### 6. 检索编排 (Retriever)

**目标：** 组合 Embedding 和 VectorStore，提供统一的检索服务。

**核心文件：** `app/rag/retriever.py`

```
Retriever
├── index_chunks(chunks)  → 批量 Embedding → upsert
├── search(query, top_k)  → embed_query → vector_search → RetrievedChunk[]
└── format_context(chunks)→ 拼接 LLM 上下文文本
```

**数据流：**
```
用户提问 → embed_query() → 向量搜索 → 召回 Top-K
    → RetrievedChunk[] → format_context()
    → [上下文 + 用户问题] → QwenLLM.generate() → 回答
```

### 7. 文档切分器 (TextChunker)

**目标：** 将长文档切分为固定窗口 + 重叠区域的文本块。

**核心文件：** `app/rag/chunker.py`

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `chunk_size` | 500 | 切分窗口大小（字符数） |
| `chunk_overlap` | 50 | 相邻窗口重叠区域（字符数） |

**扩展性：** 接口为 `split_text(text) → list[TextChunk]`，后续可替换为 Markdown 按标题切分、语义切分等策略，无需修改服务层。

---

## 四、认证层

### 8. JWT 认证与角色权限

**目标：** 提供安全的用户注册登录、JWT 签发校验、角色权限控制。

**核心文件：** `app/services/auth.py` + `app/api/auth.py` + `app/api/tickets.py`

**技术栈：**
- 密码哈希：`passlib.hash.pbkdf2_sha256`
- JWT 令牌：`PyJWT`（`pyjwt`，不是 `PyJWT`）
- 依赖注入：FastAPI `Depends` 链

**角色矩阵：**

| 资源 | customer | agent | admin |
|------|----------|-------|-------|
| 注册/登录 | ✅ | - | - |
| 查看自己工单 | ✅ | ✅ | ✅ |
| 查看所有工单 | ❌ | 分配的 | ✅ |
| 知识库上传 | ✅ | ✅ | ✅ |
| 知识库删除 | ❌ | ❌ | ✅ |

**API 端点：**

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/auth/register` | 注册（固定 customer 角色） | 无 |
| POST | `/auth/login` | 登录返回 JWT | 无 |
| GET | `/auth/me` | 当前用户信息 | ✅ Bearer Token |
| POST | `/chat` | 客服对话 | ✅ |
| POST | `/documents/upload` | 上传知识库文档 | ✅ |
| DELETE | `/documents/{id}` | 删除文档（需 admin） | ✅ |

---

## 五、工单系统

### 9. 工单与消息模型

**目标：** 支持转人工流程，记录工单状态和消息历史。

**核心文件：** `app/models/ticket.py` + `app/schemas/ticket.py` + `app/api/tickets.py`

**状态机：**
```
open → assigned → resolved → closed
  ↓        ↓
  └──→ 可直接关闭 ←──┘
```

**优先级：** low / normal / high / urgent

**API 端点：**

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/tickets` | 工单列表（customer 只看自己，admin 看全部） | ✅ 登录 |
| GET | `/tickets/{id}` | 工单详情（含消息记录） | ✅ 本人/admin |

**消息类型：** text / image / system

---

## 六、工作流

### 10. LangGraph 客服工作流

**目标：** 使用 LangGraph 构建「意图分类 → 条件路由 → 工具执行 → LLM 生成」的客服流程。

**核心文件：** `app/workflow/customer_service.py`

**工作流图：**
```
         ┌───────────────┐
         │   START       │
         └───────┬───────┘
                 │
         ┌───────▼───────┐
         │ classify_intent│
         │ (关键词分类)    │
         └───────┬───────┘
                 │
       ┌─────────┼──────────┐
       ▼         ▼          ▼
  ┌────────┐ ┌────────┐ ┌──────────┐
  │knowledge│ │ order   │ │ transfer │
  │_search  │ │_lookup  │ │_to_human │
  └────┬───┘ └────┬───┘ └─────┬────┘
       │          │           │
       ▼          ▼           ▼
  ┌───────────────────────────────┐
  │             END                │
  └───────────────────────────────┘
```

**意图分类器：**
- `knowledge`：知识库问答（默认路由）
- `order`：订单查询（触发 `lookup_order` 工具）
- `human`：转人工（创建工单，返回 ticket_id）

**LLM 降级策略：** LLM 生成失败时，直接返回检索结果的第一条内容，不阻断客服流程。

---

## 七、稳定性

### 11. 重试/熔断/降级

**目标：** 外部依赖（API 调用、数据库查询）不可靠时，自动重试和熔断保护。

**核心文件：** `app/stability/resilience.py`

**组件：**

| 组件 | 说明 | 参数 |
|------|------|------|
| `CircuitBreaker` | 连续失败 N 次后熔断 M 秒，半开探测 | `failure_threshold=3`, `recovery_seconds=30` |
| `call_with_retry` | 指数退避重试，可选超时和熔断器 | `retries=2`, `backoff_seconds=0.05` |

**组合使用：**
```python
breaker = CircuitBreaker()

result = call_with_retry(
    operation=lambda: api_call(),
    retries=2,
    timeout_seconds=5,
    breaker=breaker,
)
```

### 12. 滑动窗口限流

**目标：** 按用户身份限流，防止恶意请求或突发流量压垮服务。

**核心文件：** `app/stability/rate_limit.py` + `app/stability/factory.py`

**实现策略：**
- **Redis 可用时**：使用 Sorted Set 滑动窗口，精确计数
- **Redis 不可用时**：回退到进程内 `deque` 滑动窗口
- **限流禁用时**：`AllowAllRateLimiter` 显式放行

**配置：**
```
RATE_LIMIT_REQUESTS=60          # 窗口内允许的请求数
RATE_LIMIT_WINDOW_SECONDS=60    # 窗口时间（秒）
```

### 13. Prometheus 指标

**目标：** 暴露 Prometheus 文本格式的请求指标，无需第三方 exporter。

**核心文件：** `app/stability/metrics.py`

**暴露的指标：**
```
# 请求总数
customer_service_requests_total

# 被限流的请求数
customer_service_rate_limited_total

# HTTP 状态码分布
customer_service_http_responses_total{status_code="200"}
customer_service_http_responses_total{status_code="429"}

# 意图分布
customer_service_intents_total{intent="knowledge"}
customer_service_intents_total{intent="order"}
customer_service_intents_total{intent="human"}
```

**访问方式：** `GET /metrics` → `PlainTextResponse`

---

## 八、容器化部署

### 14. Docker 多阶段构建与编排

**目标：** 提供可复现的容器化构建和一套完整的服务编排。

**核心文件：** `Dockerfile` + `docker-compose.yml`

**Dockerfile 多阶段构建：**
```
阶段一 builder：安装 gcc + libpq-dev → pip install 依赖
阶段二 runtime：仅复制 libpq5 运行时库 + 已安装的 Python 包
```

**最终镜像体积：** ≈ 250MB（仅运行时必需组件）

**Docker Compose 编排：**

| 服务 | 镜像 | 说明 |
|------|------|------|
| `app` | 自定义构建 | FastAPI 应用，2 workers |
| `postgres` | postgres:16-alpine | 主数据库 |
| `redis` | redis:7-alpine | 缓存与共享状态 |
| `milvus` (可选) | milvusdb/milvus | 向量数据库 |

**启动命令：**
```bash
# 完整启动
docker compose up --build -d

# 仅应用 + 必需依赖
docker compose up --build -d app

# 查看日志
docker compose logs -f
```

---

## 前端架构

**目标：** 提供完整的用户交互界面，与后端 API 完全对齐。

**技术栈：** Next.js 15 + TypeScript + Shadcn UI + Tailwind CSS

**文件结构：**
```
frontend/src/
├── app/
│   ├── page.tsx              # 首页/登录引导
│   ├── login/page.tsx        # 登录页
│   ├── register/page.tsx     # 注册页
│   ├── chat/page.tsx         # 客服对话页
│   └── tickets/page.tsx      # 我的工单页
├── components/ui/            # Shadcn UI 组件
├── lib/
│   ├── api.ts                # API 客户端，自动管理 JWT
│   └── utils.ts              # 工具函数
└── proxy.ts                  # Next.js 路由守卫
```

**API 客户端封装：** `lib/api.ts` 统一处理：
- JWT Token 的 localStorage + cookie 双存储
- `Authorization: Bearer <token>` 自动注入
- 401 错误统一处理
- 类型安全（TypeScript 接口与后端 Pydantic 对齐）

**路由守卫：** `proxy.ts` 中间件：
- 未登录访问 `/chat`、`/tickets` → 重定向到 `/login`
- 已登录访问 `/login`、`/register` → 重定向到 `/chat`

---

## 附录：架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Next.js 前端 (Shadcn UI)                      │
│  ┌──────┐  ┌──────┐  ┌──────────┐  ┌──────────┐                     │
│  │ 首页  │  │ 登录  │  │ 客服对话   │  │ 我的工单   │                     │
│  └──────┘  └──────┘  └────┬─────┘  └────┬─────┘                     │
│                           │             │                             │
│                    ┌──────▼─────────────▼──────┐                     │
│                    │  api.ts (JWT 自动管理)      │                     │
│                    └──────────────────────────┘                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────────────┐
│                   FastAPI (uvicorn, 2 workers)                       │
│                                                                      │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ Auth    │ │ Chat    │ │Documents │ │ Tickets  │ │ /metrics     │ │
│  │ API     │ │ API     │ │ API      │ │ API      │ │ Prometheus    │ │
│  └────┬────┘ └────┬────┘ └────┬─────┘ └────┬─────┘ └──────────────┘ │
│       │           │           │             │                          │
│       ▼           ▼           ▼             ▼                          │
│  ┌──────────┐ ┌──────────────────────┐  ┌───────────┐                 │
│  │JWT Auth  │ │ Workflow (LangGraph) │  │Ticket/Msg │                 │
│  │Service   │ │  ┌─────────────────┐ │  │Model      │                 │
│  │          │ │  │ classify → route│ │  └───────────┘                 │
│  │PBKDF2    │ │  │ → tools → LLM  │ │                                │
│  │PyJWT     │ │  └─────────────────┘ │                                │
│  └──────────┘ └──────────┬───────────┘                                │
│                          │                                            │
│          ┌───────────────┼───────────────┐                            │
│          ▼               ▼               ▼                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                      │
│  │  Retriever  │  │ RateLimit  │  │  Metrics    │                     │
│  │  (Embedding │  │ SlidingWin │  │  Prometheus  │                     │
│  │   + Vector) │  │ + Redis   │  │  format     │                     │
│  └───────┬────┘  └────────────┘  └────────────┘                      │
│          │                                                           │
│  ┌───────┴───────────────┐                                           │
│  │  Embedding Provider    │  ┌──────────────┐                        │
│  │  ┌────────┐┌────────┐ │  │  Circuit      │                       │
│  │  │  Mock  ││DashScope│ │  │  Breaker      │                       │
│  │  └────────┘└────────┘ │  │  + Retry      │                       │
│  │  Vector Store         │  └──────────────┘                        │
│  │  ┌────────┐┌────────┐ │                                           │
│  │  │InMemory││ Milvus │ │                                           │
│  │  └────────┘└────────┘ │                                           │
│  └───────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
  │  PostgreSQL   │  │    Redis       │  │   Milvus      │
  │  (主数据库)     │  │  (缓存/限流)    │  │ (向量数据库)    │
  └───────────────┘  └───────────────┘  └───────────────┘
```

---

## 附录：替换方案对照表

| 模块 | 开发原型 | 生产级方案 | 切换方式 | 回退策略 |
|------|---------|-----------|---------|---------|
| 配置 | 硬编码/散落 `os.getenv` | `pydantic-settings` 集中管理 | 设置 `.env` | 默认值开发模式 |
| 数据库 | 手动 SQLite | SQLAlchemy ORM + PostgreSQL | 修改 `DATABASE_URL` | 自动识别 SQLite |
| Embedding | 简单随机向量 | DashScope text-embedding-v3 | 设置 `DASHSCOPE_API_KEY` | 自动回退 Mock |
| 向量库 | 内存列表 | Milvus 分布式 | 设置 `MILVUS_URI` | 自动回退 InMemory |
| LLM | 无 | QwenLM (qwen-plus) | 设置 `DASHSCOPE_API_KEY` | 跳过 LLM 生成 |
| 限流 | 无 | 滑动窗口 + Redis | 设置 `REDIS_URL` | 进程内 `deque` |
| 会话记忆 | 无 | Redis + 进程内 | 设置 `REDIS_URL` | 进程内字典 |
| 部署 | 手动 `uvicorn` | Docker Compose 编排 | `docker compose up` | 单机开发模式 |