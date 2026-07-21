# Section 4: Milvus 生产级向量库

## 学习目标
1. 理解 Milvus 的架构和核心概念
2. 使用 Docker 部署 Milvus 服务
3. 使用 pymilvus SDK 进行 CRUD 操作
4. 将 Milvus 集成到 LangChain RAG 链路

## 技术栈
- **向量数据库**: Milvus 2.x（Docker 部署）
- **Python SDK**: pymilvus
- **Embedding**: fastembed + BAAI/bge-small-zh-v1.5（本地模型）
- **LLM**: GLM-4-Flash（智谱 API）
- **框架**: LangChain + langchain-milvus

## 为什么选 Milvus？

| 对比维度 | FAISS | Chroma | Milvus |
|----------|-------|--------|--------|
| 定位 | 向量检索库 | 轻量级向量数据库 | 生产级向量数据库 |
| 持久化 | 需手动管理 | 自动 | 自动 |
| 分布式 | 不支持 | 不支持 | 支持 |
| 数据规模 | 百万级 | 十万级 | 十亿级 |
| 索引类型 | 丰富 | 有限 | 最丰富 |
| 适用场景 | 本地实验 | 原型开发 | 生产环境 |

## 核心概念

### Collection（集合）
相当于关系数据库的"表"，包含 Schema 定义和数据。

### Schema（模式）
定义字段结构：
- `id`：主键（自动生成）
- `vector`：向量字段（指定维度）
- `text`：原始文本字段
- 其他自定义字段（metadata）

### Index（索引）
向量索引类型：
- `IVF_FLAT`：倒排索引 + 暴力搜索，适合中小规模
- `IVF_SQ8`：倒排 + 标量量化，节省内存
- `HNSW`：图索引，查询快但占用内存大
- `DISKANN`：磁盘索引，适合超大规模

### Search（搜索）
- 向量相似度搜索
- 支持过滤条件（标量过滤）
- 支持 Top-K 查询

## Docker 部署

```bash
# 拉取 Milvus 镜像（standalone 模式）
docker pull milvusdb/milvus:v2.4-latest

# 启动 Milvus（简化版，适合开发测试）
docker run -d --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  -v /path/to/data:/var/lib/milvus \
  milvusdb/milvus:v2.4-latest

# 或使用 docker-compose（推荐，包含 etcd + minio + milvus）
# 下载 docker-compose.yml
curl -L https://github.com/milvus-io/milvus/releases/download/v2.4.0/milvus-standalone-docker-compose.yml -o docker-compose.yml
docker-compose up -d
```

### 连接信息
- Host: `localhost`
- Port: `19530`
- Web UI: `http://localhost:9091`（Milvus Birdwatcher）

## 代码结构

### demo1_milvus_basic.py
pymilvus 基础操作：
1. 连接 Milvus
2. 创建 Collection（定义 Schema + Index）
3. 插入向量数据
4. 向量相似度搜索
5. 带过滤条件的搜索
6. 删除数据

### demo2_milvus_langchain_rag.py
Milvus + LangChain RAG 集成：
1. 使用 langchain-milvus 连接 Milvus
2. 文档分块 + 向量化 + 存储到 Milvus
3. 构建 RAG 检索链
4. 端到端问答

## 注意事项
- Milvus standalone 需要 Docker 环境
- 本地开发可用 Milvus Lite（嵌入式，无需 Docker）
- 生产环境建议使用 Milvus Cluster（Kubernetes 部署）
