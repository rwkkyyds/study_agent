"""
demo1_embedding_batch.py — Embedding 批处理优化吞吐

学习目标：
1. 理解为什么批量 Embedding 比单条快：模型推理的矩阵乘法天然适合批处理
2. 对比不同 batch_size 的吞吐差异（docs/sec）
3. 掌握 fastembed / sentence-transformers 的 batch encode API

运行：python demo1_embedding_batch.py
首次运行自动下载模型（BAAI/bge-small-zh-v1.5，约 100MB）
"""

import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def load_model():
    """加载 Embedding 模型（单例，只加载一次）"""
    from fastembed import TextEmbedding
    # fastembed 的 BGE-small：轻量、本地运行、无需 GPU
    logger.info("加载模型 BAAI/bge-small-zh-v1.5 ...（首次需下载）")
    model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    logger.info("模型加载完成")
    return model


# ================================================
# Part 1：单条 Embedding — 一次编码一条
# ================================================
def demo_single_embedding(model, texts):
    """逐条编码：for 循环一次处理一条"""
    logger.info("-- Part 1: 单条 Embedding --")
    embeddings = []
    t0 = time.perf_counter()

    for text in texts:
        emb = list(model.embed([text]))  # 每次只传 1 条
        embeddings.append(emb)

    elapsed = time.perf_counter() - t0
    logger.info(f"  处理 {len(texts)} 条，耗时 {elapsed:.2f}s")
    logger.info(f"  吞吐：{len(texts) / elapsed:.1f} docs/sec")
    return elapsed


# ================================================
# Part 2：批量 Embedding — 一次编码一批
# ================================================
def demo_batch_embedding(model, texts, batch_size):
    """批量编码：一次传一个 batch，利用矩阵乘法加速"""
    logger.info(f"-- Part 2: 批量 Embedding (batch_size={batch_size}) --")
    t0 = time.perf_counter()

    embeddings = list(model.embed(texts, batch_size=batch_size))

    elapsed = time.perf_counter() - t0
    logger.info(f"  处理 {len(texts)} 条，耗时 {elapsed:.2f}s")
    logger.info(f"  吞吐：{len(texts) / elapsed:.1f} docs/sec")
    return elapsed


# ================================================
# Part 3：不同 batch_size 对比
# ================================================
def demo_batch_size_comparison(model, texts):
    """逐个 batch_size 测试，找最优值"""
    logger.info("-- Part 3: 不同 batch_size 对比 --")

    results = []
    for bs in [1, 4, 8, 16, 32, 64, 128]:
        t0 = time.perf_counter()
        # 每个 batch_size 跑 3 轮取平均，减少偶然波动
        for _ in range(3):
            list(model.embed(texts, batch_size=bs))
        elapsed = time.perf_counter() - t0
        avg_elapsed = elapsed / 3
        throughput = len(texts) / avg_elapsed
        results.append((bs, avg_elapsed, throughput))
        logger.info(f"  batch_size={bs:>3}: {avg_elapsed:.2f}s, {throughput:.0f} docs/sec")

    return results


# ================================================
# Main
# ================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Embedding 批处理优化演示")
    print("=" * 60)

    model = load_model()

    # 准备测试数据：模拟 200 条文档
    texts = [
        f"这是第 {i} 条测试文档，用来模拟批量向量化的性能对比实验。" for i in range(200)
    ]

    print(f"\n准备 {len(texts)} 条文档，开始测试...\n")

    # Part 1：单条
    single_time = demo_single_embedding(model, texts)

    # Part 2：批量
    batch_time = demo_batch_embedding(model, texts, batch_size=32)

    speedup = single_time / batch_time
    print(f"\n  加速比：{speedup:.1f}x")
    print(f"  单条 {single_time:.1f}s -> 批量(batch=32) {batch_time:.1f}s")
    print(f"  原因：GPU/CPU 矩阵运算同时处理 32 条，而不是 1 条 1 次")

    # Part 3：对比不同 batch_size
    print("\n")
    results = demo_batch_size_comparison(model, texts)

    print("\n-- 汇总 --")
    print(f"  {'batch_size':<12}{'耗时(s)':<12}{'吞吐(docs/sec)':<16}{'加速比'}")
    print("  " + "-" * 48)
    baseline = results[0][1]  # batch_size=1 的"耗时"作为基准 
    for bs, elapsed, throughput in results:
        sp = baseline / elapsed
        print(f"  {bs:<12}{elapsed:<12.2f}{throughput:<16.0f}{sp:.1f}x")

    print("\n  > batch_size 越大吞吐越高，但边际递减（32->64 提升已很小）")
    print("  > batch_size 过大会 OOM，需根据显存/内存选合适值")
    print("\n[OK] demo1 完成！")
