"""
demo3_pipeline_batch.py — 检索 + 重排管道批处理优化

学习目标：
1. 理解完整检索管道的两个批处理机会：建索引（批量 Embedding）+ 重排（批量 Rerank）
2. 对比 naive（逐条）vs optimized（批量）管道的端到端耗时
3. 量化每个阶段的加速效果

运行：python demo3_pipeline_batch.py
首次运行自动下载模型。

管道流程：
  文档 -> [批量Embedding] -> FAISS索引 -> 检索Top-K -> [批量Rerank] -> 最终结果
         ^ 优化点1                 ^ 向量检索          ^ 优化点2
"""

import time
import logging
import random
import string

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def load_models():
    """加载 Embedding 和 Reranker 模型"""
    from fastembed import TextEmbedding
    from flashrank import Ranker
    from flashrank.Ranker import RerankRequest

    logger.info("加载模型...")
    emb_model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
    logger.info("模型加载完成")
    return emb_model, ranker, RerankRequest


def make_docs(count):
    """生成模拟文档"""
    topics = ["Python性能优化", "PostgreSQL索引原理", "Redis缓存策略",
              "Docker容器化部署", "RESTful API设计", "消息队列选型",
              "微服务拆分原则", "异步任务队列"]
    docs = []
    for i in range(count):
        topic = random.choice(topics)
        docs.append(f"文档{i}: {topic}相关 - {''.join(random.choices(string.ascii_letters + ' ', k=60))}")
    return docs


# ================================================
# Part 1：Naive 管道 — 逐条 Embedding + 逐条 Rerank
# ================================================
def demo_naive_pipeline(emb_model, ranker, RerankRequest, docs, query):
    """
    Naive 管道：每个阶段都逐条处理，无视批处理优化
    """
    logger.info("\n-- Part 1: Naive 管道（逐条处理）--")
    total_t0 = time.perf_counter()

    # 阶段1：逐条 Embedding 建索引
    stage_t0 = time.perf_counter()
    vectors = []
    for doc in docs:
        emb = list(emb_model.embed([doc]))
        vectors.append(emb[0])
    emb_time = time.perf_counter() - stage_t0

    # 阶段2：FAISS 检索
    import numpy as np
    import faiss

    stage_t0 = time.perf_counter()
    vectors_np = np.array(vectors).astype("float32")
    dim = vectors_np.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(vectors_np)
    index.add(vectors_np)

    query_emb = np.array(list(emb_model.embed([query]))[0]).astype("float32").reshape(1, -1)
    faiss.normalize_L2(query_emb)
    D, I = index.search(query_emb, k=20)
    search_time = time.perf_counter() - stage_t0

    # 阶段3：逐条 Rerank
    stage_t0 = time.perf_counter()
    top_docs = [{"id": int(I[0][j]), "text": docs[I[0][j]]} for j in range(20)]
    reranked = []
    for d in top_docs:
        request = RerankRequest(query=query, passages=[d])
        scored = ranker.rerank(request)
        reranked.append(scored[0])
    reranked.sort(key=lambda x: x["score"], reverse=True)
    rerank_time = time.perf_counter() - stage_t0

    total = time.perf_counter() - total_t0

    logger.info(f"  逐条Embedding: {emb_time:.2f}s")
    logger.info(f"  FAISS检索:    {search_time:.2f}s")
    logger.info(f"  逐条Rerank:    {rerank_time:.2f}s")
    logger.info(f"  总耗时:        {total:.2f}s")

    return {"embedding": emb_time, "search": search_time, "rerank": rerank_time, "total": total}


# ================================================
# Part 2：优化管道 — 批量 Embedding + 批量 Rerank
# ================================================
def demo_optimized_pipeline(emb_model, ranker, RerankRequest, docs, query):
    """
    优化管道：利用批处理加速 Embedding 和 Rerank 阶段
    """
    logger.info("\n-- Part 2: 优化管道（批量处理）--")
    total_t0 = time.perf_counter()

    import numpy as np
    import faiss

    # 阶段1：批量 Embedding（batch_size=32）
    stage_t0 = time.perf_counter()
    vectors = list(emb_model.embed(docs, batch_size=32))
    emb_time = time.perf_counter() - stage_t0

    # 阶段2：FAISS 检索
    stage_t0 = time.perf_counter()
    vectors_np = np.array(vectors).astype("float32")
    dim = vectors_np.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(vectors_np)
    index.add(vectors_np)

    query_emb = np.array(list(emb_model.embed([query], batch_size=32))[0]).astype("float32").reshape(1, -1)
    faiss.normalize_L2(query_emb)
    D, I = index.search(query_emb, k=20)
    search_time = time.perf_counter() - stage_t0

    # 阶段3：批量 Rerank（一次传全部 20 条）
    stage_t0 = time.perf_counter()
    top_docs = [{"id": int(I[0][j]), "text": docs[I[0][j]]} for j in range(20)]
    request = RerankRequest(query=query, passages=top_docs)
    reranked = ranker.rerank(request)
    rerank_time = time.perf_counter() - stage_t0

    total = time.perf_counter() - total_t0

    logger.info(f"  批量Embedding: {emb_time:.2f}s")
    logger.info(f"  FAISS检索:    {search_time:.2f}s")
    logger.info(f"  批量Rerank:    {rerank_time:.2f}s")
    logger.info(f"  总耗时:        {total:.2f}s")

    logger.info(f"  Top-1: {reranked[0]['text'][:50]}... (score={reranked[0]['score']:.4f})")

    return {"embedding": emb_time, "search": search_time, "rerank": rerank_time, "total": total}


# ================================================
# Main
# ================================================
if __name__ == "__main__":
    print("=" * 60)
    print("检索管道批处理优化对比")
    print("=" * 60)

    emb_model, ranker, RerankRequest = load_models()
    docs = make_docs(500)
    query = "如何提升数据库查询性能？"

    print(f"\n文档数：{len(docs)}")
    print(f"查询：{query}\n")

    naive = demo_naive_pipeline(emb_model, ranker, RerankRequest, docs, query)
    optimized = demo_optimized_pipeline(emb_model, ranker, RerankRequest, docs, query)

    print("\n-- 对比汇总 --")
    print(f"  {'阶段':<16}{'Naive':<12}{'优化后':<12}{'加速比':<8}{'节省'}")
    print("  " + "-" * 56)
    for stage, label in [("embedding", "Embedding"), ("search", "FAISS检索"), ("rerank", "Rerank"), ("total", "总耗时")]:
        t_naive = naive[stage]
        t_opt = optimized[stage]
        sp = t_naive / t_opt if t_opt > 0 else 1
        saved = t_naive - t_opt
        print(f"  {label:<16}{t_naive:<12.2f}{t_opt:<12.2f}{sp:<8.1f}x{saved:.1f}s")

    print(f"\n  > 总加速比：{naive['total'] / optimized['total']:.1f}x")
    print("  > Embedding 加速最明显：batch_size=32 利用矩阵乘法并行")
    print("  > Rerank 加速也很显著：20 个 pair 一次传入 vs 20 次独立调用")
    print("\n[OK] demo3 完成！")
