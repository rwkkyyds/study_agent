# Section 6：Embedding / Reranker 批处理优化吞吐

## 学习目标

1. 理解单条处理 vs 批量处理的吞吐差异（io-bound vs compute-bound）
2. 掌握 Embedding 模型批处理：batch_size 对吞吐的影响
3. 掌握 Reranker 模型批处理：pairwise 批量打分
4. 学会用 `sentence-transformers` / `fastembed` / `FlashRank` 的 batch encode API
5. 量化对比：docs/sec、tokens/sec、加速比

## 学习顺序

| 顺序 | 文件 | 内容 | 核心技能 |
|------|------|------|----------|
| 1 | `demo1_embedding_batch.py` | 单条 Embedding vs 批量 Embedding，batch_size 对吞吐的影响 | Embedding 批处理 |
| 2 | `demo2_reranker_batch.py` | 单条 Rerank vs 批量 Rerank，pairwise 批量打分 | Reranker 批处理 |
| 3 | `demo3_pipeline_batch.py` | 整合检索+重排管道，对比优化前后吞吐 | 管道级优化 |

## 运行方式

```bash
pip install fastembed FlagEmbedding sentence-transformers numpy

# 直接运行，无需 Docker
python demo1_embedding_batch.py
python demo2_reranker_batch.py
python demo3_pipeline_batch.py
```

> 首次运行会自动下载模型（约100-500MB），需等待下载完成。

## 前置知识

- Week_1 Section_4：Embedding 与向量库
- Week_2 Section_2：混合检索与重排（Reranker 基础）

## 推荐复习

- Week_4 Section_4：asyncio 高并发（理解 io-bound 优化）
- Week_4 Section_5：Celery 异步任务（批量异步任务分发）

## 下一节

**Section_7 压测与量化**：Locust 压测、QPS/P99 指标量化优化
