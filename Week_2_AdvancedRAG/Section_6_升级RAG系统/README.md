# Section 6: 升级 RAG 系统（Week 2 周 Demo）

## 学习目标
1. 将 Week 2 所学组件集成到一个完整的 RAG 系统
2. 对比 Naive RAG vs Advanced RAG 的效果差异
3. 掌握生产级 RAG 系统的架构设计

## 技术栈
- **文档解析**: pdfplumber（按元素类型解析，表格整体保留）
- **向量库**: Milvus（Docker 部署，pymilvus SDK）
- **Embedding**: fastembed + BAAI/bge-small-zh-v1.5
- **BM25**: rank_bm25（稀疏检索）
- **Rerank**: sentence-transformers CrossEncoder（BAAI/bge-reranker-base）
- **LLM**: GLM-4-Flash（智谱 API）
- **框架**: LangChain LCEL

## Week 2 知识点集成

```
Section 1: Query Transformation → 多查询改写
Section 2: 混合检索 + Rerank   → BM25+向量 + CrossEncoder
Section 3: RAG 评估             → 效果量化
Section 4: Milvus               → 生产级向量库
Section 5: 复杂文档解析          → 表格不切碎
    ↓
Section 6: 集成所有组件 → 完整的 Advanced RAG 系统
```

## Advanced RAG 架构

```
用户问题
    ↓
[1] 混合检索
    ├── BM25 稀疏检索（关键词匹配）
    └── Milvus 向量检索（语义匹配）
    ↓
[2] RRF 融合排序
    ↓
[3] Rerank 重排（CrossEncoder 精排）
    ↓
[4] Top-K 文档 → Prompt → LLM → 回答
```

## 运行方式（Docker 容器，生产级）

```bash
# 1. 确保 Milvus 服务运行
cd ../Section_4_Milvus向量库 && docker compose up -d

# 2. 构建 RAG 容器
docker build -t rag-demo .

# 3. 运行（--add-host 让容器访问宿主机的 Milvus）
docker run --rm --add-host host.docker.internal:host-gateway rag-demo
```

## Windows DLL 冲突解决方案

`sentence-transformers` 依赖 PyTorch，Windows 上常有 `c10.dll` 加载失败问题。
**生产级方案**：用 Docker 容器运行，彻底隔离依赖冲突。

| 方案 | 优点 | 缺点 |
|------|------|------|
| Docker 容器 | 彻底隔离，可复现 | 需要 Docker Desktop |
| Linux 虚拟机 | 完整 Linux 环境 | 资源占用大 |
| WSL2 + Conda | 接近 Linux | 配置复杂 |

## 注意事项
- CrossEncoder 模型约 1.1GB，首次运行会自动下载到容器内
- Milvus 服务需要提前启动（端口 19530）
- 智谱 API Key 写在代码中，生产环境应使用环境变量
