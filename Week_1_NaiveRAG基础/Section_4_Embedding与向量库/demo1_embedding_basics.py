"""
Demo 1: Embedding 基础 — 文本向量化与相似度计算
学习目标：理解 Embedding 的核心原理，掌握向量相似度计算
运行方式：python demo1_embedding_basics.py

核心概念：
  Embedding = 把文本变成一组数字（向量）
  语义相似的文本 -> 向量距离近
  语义不同的文本 -> 向量距离远
"""

import numpy as np
import hashlib


# ========== 1. 用 LLM 模拟 Embedding（概念演示） ==========
# 真实场景用专门的 Embedding 模型（如 text-embedding-3-small）
# 这里先用简单方式演示"文本 -> 向量"的概念

print("=" * 60)
print("【1. Embedding 核心概念】")
print("""
  Embedding 的作用：
    "猫坐在垫子上" -> [0.2, 0.8, -0.1, 0.5, ...]  (1536维向量)
    "小猫趴在垫子" -> [0.21, 0.79, -0.12, 0.48, ...]  (相似向量)
    "今天天气真好" -> [-0.5, 0.1, 0.9, -0.3, ...]  (不同向量)

  关键特性：
    1. 语义相似的文本，向量距离近（余弦相似度高）
    2. 语义不同的文本，向量距离远（余弦相似度低）
    3. 支持数学运算（向量加减、相似度计算）
""")


# ========== 2. 余弦相似度计算 ==========
print("=" * 60)
print("【2. 余弦相似度 — 衡量两个向量的相似程度】")

def cosine_similarity(vec_a, vec_b):
    """
    余弦相似度 = 两个向量的夹角余弦值
    范围：[-1, 1]
      1 = 完全相同方向（语义一致）
      0 = 正交（无关）
     -1 = 完全相反（语义对立）
    """
    #vec_a 和 vec_b 都是向量（列表或 numpy 数组）
    #eg: vec_a = [0.9, 0.8, 0.1, 0.2], vec_b = [0.85, 0.75, 0.15, 0.25]
    dot_product = np.dot(vec_a, vec_b) # 点积 eg: 0.9*0.85 + 0.8*0.75 + 0.1*0.15 + 0.2*0.25
    norm_a = np.linalg.norm(vec_a) # 向量长度 eg: sqrt(0.9^2 + 0.8^2 + 0.1^2 + 0.2^2)
    norm_b = np.linalg.norm(vec_b)
    return dot_product / (norm_a * norm_b) # 余弦相似度计算公式 eg: dot_product / (norm_a * norm_b)

# 用简单向量演示
vec_cat = np.array([0.9, 0.8, 0.1, 0.2])      # "猫"
vec_dog = np.array([0.85, 0.75, 0.15, 0.25])   # "狗"（和猫相似）
vec_car = np.array([0.1, 0.2, 0.9, 0.85])      # "汽车"（和猫不同）

print(f"  猫 vs 狗:   {cosine_similarity(vec_cat, vec_dog):.4f}  (高相似度)")
print(f"  猫 vs 汽车: {cosine_similarity(vec_cat, vec_car):.4f}  (低相似度)")
print(f"  狗 vs 汽车: {cosine_similarity(vec_dog, vec_car):.4f}  (低相似度)")
print()


# ========== 3. 本地 Embedding 模拟 ==========
print("=" * 60)
print("【3. Embedding 实现 — 本地哈希模拟（概念演示）】")
print("""
  真实场景使用专门的 Embedding 模型：
    - OpenAI text-embedding-3-small（1536维）
    - GLM embedding-3（2048维）
    - BAAI/bge-small-zh-v1.5（512维，中文开源）

  这里用哈希模拟"文本 -> 向量"的过程，
  展示 Embedding 的核心特性：相似文本 -> 相似向量。
""")


def text_to_vector(text: str, dim: int = 64) -> list[float]: #dim 是向量维度，真实模型通常是512、768、1536等
    """
    用哈希生成伪向量（仅用于演示概念）
    真实 Embedding 会用神经网络生成语义向量
    """
    hash_bytes = hashlib.md5(text.encode()).digest() #text 转为字节，计算 MD5 哈希值，得到一个固定长度的字节串（16字节）
    # 用哈希生成多个维度的值
    vectors = []
    for i in range(dim):
        seed = hashlib.md5(hash_bytes + bytes([i])).digest() 
        #在原哈希基础上加上维度索引，生成不同的哈希值，保证每个维度的值不同
        val = int.from_bytes(seed[:4], "little") / (2**32)
          #取前4字节，转换为整数，归一化到 [0, 1] 范围
        vectors.append(val * 2 - 1)  
        # 归一化到 [-1, 1]
    return vectors


# 测试文本
texts = [
    "FastAPI 是 Python Web 框架",
    "FastAPI是一个现代的Python Web框架",
    "今天天气真不错",
    "向量数据库用于存储和检索向量",
    "Chroma 是一个轻量级向量数据库",
]

# 获取 Embedding
vectors = [text_to_vector(t) for t in texts]
print(f"  文本数量: {len(texts)}")
print(f"  向量维度: {len(vectors[0])}")
print()

# 计算相似度矩阵
print("  相似度矩阵:")
print(f"  {'':30s}", end="")
for i in range(len(texts)):
    print(f"  [{i}]", end="")
print()

for i, text_i in enumerate(texts):
    print(f"  [{i}] {text_i[:28]:28s}", end="")
    for j in range(len(texts)):
        sim = cosine_similarity(
            np.array(vectors[i]),
            np.array(vectors[j])
        )
        print(f"  {sim:.2f}", end="")
    print()

print()
print("  预期结果：")
print("    [0] 和 [1] 相似度最高（都在说 FastAPI）")
print("    [3] 和 [4] 相似度较高（都在说向量数据库）")
print("    [2] 和其他相似度低（天气 vs 技术）")
print()


# ========== 4. Embedding 的实际应用 ==========
print("=" * 60)
print("【4. Embedding 在 RAG 中的位置】")
print("""
  原始文档 -> 分块 -> Embedding(每个块转为向量) -> 存入向量数据库
                                                    │
  用户问题 -> Embedding(问题转为向量) -> 向量数据库相似度检索
                                                    │
                                        返回最相似的文档块 -> LLM 生成回答

  Embedding 是连接"文本世界"和"向量世界"的桥梁。
""")
