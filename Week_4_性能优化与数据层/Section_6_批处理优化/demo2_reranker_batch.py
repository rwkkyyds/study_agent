"""
demo2_reranker_batch.py — Reranker 批处理优化吞吐

学习目标：
1. 理解 Reranker 的 pairwise 打分模式：每个 (query, doc) 对独立计算
2. 掌握批量 rerank：一次传多个 (query, doc) 对，而非逐对调用
3. 对比单条 vs 批量 Rerank 的吞吐差异

运行：python demo2_reranker_batch.py
首次运行自动下载模型（ms-marco-MiniLM-L-12-v2，约 22MB）
"""

import time
import logging
import random
import string

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def load_reranker():
    """加载 Reranker 模型"""
    from flashrank import Ranker
    from flashrank.Ranker import RerankRequest
    logger.info("加载 Reranker 模型 ms-marco-MiniLM-L-12-v2 ...（首次需下载）")
    ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
    logger.info("模型加载完成")
    return ranker, RerankRequest


def make_passages(count):
    """生成模拟文档段落"""
    topics = ["深度学习", "数据库优化", "微服务架构", "自动驾驶", "自然语言处理",
              "推荐系统", "计算机视觉", "量化交易", "区块链", "边缘计算"]
    return [
        {"id": i, "text": f"{random.choice(topics)}相关：{''.join(random.choices(string.ascii_letters + ' ', k=100))}"}
        for i in range(count)
    ]


# ================================================
# Part 1：单条 Rerank — 一次传一个 pair
# ================================================
def demo_single_rerank(ranker, RerankRequest, query, passages):
    """逐条打分：循环调用，一次处理一个 passage"""
    logger.info("-- Part 1: 单条 Rerank --")
    t0 = time.perf_counter()

    results = []
    for p in passages:
        # 每次只传 1 个 passage -> 效率低下
        request = RerankRequest(query=query, passages=[p])
        scored = ranker.rerank(request)
        results.append(scored[0])

    elapsed = time.perf_counter() - t0
    logger.info(f"  处理 {len(passages)} 条，耗时 {elapsed:.2f}s")
    logger.info(f"  吞吐：{len(passages) / elapsed:.1f} passages/sec")
    return elapsed


# ================================================
# Part 2：批量 Rerank — 一次传全部
# ================================================
def demo_batch_rerank(ranker, RerankRequest, query, passages):
    """批量打分：一次把所有 passage 传给 ranker"""
    logger.info("-- Part 2: 批量 Rerank --")
    t0 = time.perf_counter()

    # 一次性传入所有 passages，模型内部批量处理
    request = RerankRequest(query=query, passages=passages)
    results = ranker.rerank(request)

    elapsed = time.perf_counter() - t0
    logger.info(f"  处理 {len(passages)} 条，耗时 {elapsed:.2f}s")
    logger.info(f"  吞吐：{len(passages) / elapsed:.1f} passages/sec")
    logger.info(f"  Top-1 得分：{results[0]['score']:.4f} (id={results[0]['id']})")

    return elapsed


# ================================================
# Part 3：不同批量大小的对比
# ================================================
def demo_batch_size_comparison(ranker, RerankRequest, query, all_passages, batch_sizes):
    """对比不同 batch_size：手动分 batch 传给 ranker"""
    logger.info("-- Part 3: 不同 batch_size 对比 --")

    results = []
    for bs in batch_sizes:
        t0 = time.perf_counter()
        # 把所有 passage 按 bs 分组，逐批传入
        for i in range(0, len(all_passages), bs):
            chunk = all_passages[i:i + bs]
            request = RerankRequest(query=query, passages=chunk)
            ranker.rerank(request)
        elapsed = time.perf_counter() - t0
        throughput = len(all_passages) / elapsed
        results.append((bs, elapsed, throughput))
        logger.info(f"  batch_size={bs:>3}: {elapsed:.2f}s, {throughput:.0f} passages/sec")

    return results


# ================================================
# Main
# ================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Reranker 批处理优化演示")
    print("=" * 60)

    ranker, RerankRequest = load_reranker()
    query = "如何优化数据库查询性能？"
    passages = make_passages(100)

    print(f"\n查询：{query}")
    print(f"候选文档：{len(passages)} 条\n")

    # Part 1：单条
    single_time = demo_single_rerank(ranker, RerankRequest, query, passages)

    # Part 2：批量
    batch_time = demo_batch_rerank(ranker, RerankRequest, query, passages)

    speedup = single_time / batch_time
    print(f"\n  加速比：{speedup:.1f}x")
    print(f"  单条 {single_time:.1f}s -> 批量 {batch_time:.1f}s")
    print(f"  原因：一次传入 N 个 pair，模型内部并行计算 Cross-Attention")

    # Part 3：不同分块大小的对比
    print("\n")
    batch_sizes = [1, 4, 8, 16, 32, 64, 100]
    results = demo_batch_size_comparison(ranker, RerankRequest, query, passages, batch_sizes)

    print("\n-- 汇总 --")
    print(f"  {'batch_size':<12}{'耗时(s)':<12}{'吞吐(passages/sec)':<22}{'加速比'}")
    print("  " + "-" * 52)
    baseline = results[0][1]
    for bs, elapsed, throughput in results:
        sp = baseline / elapsed
        print(f"  {bs:<12}{elapsed:<12.2f}{throughput:<22.0f}{sp:.1f}x")

    print("\n  > Reranker 加速比通常比 Embedding 更明显（Cross-Encoder 推理更重）")
    print("\n[OK] demo2 完成！")
