"""
Demo2: DeepEval 评估框架
特点：支持 pytest 集成、G-Eval 自定义评估、本地评估
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from deepeval import evaluate # DeepEval 评估函数
from deepeval.test_case import LLMTestCase # DeepEval 测试用例类
from deepeval.metrics import (  # DeepEval 内置评估指标
    FaithfulnessMetric, # 评估回答与检索上下文的一致性
    AnswerRelevancyMetric, # 评估回答与问题的相关性
    ContextualPrecisionMetric, # 评估检索到的上下文的精确性
    ContextualRecallMetric, # 评估检索到的上下文的完整性
)
from deepeval.models.base_model import DeepEvalBaseLLM # DeepEval LLM 基类
from langchain_openai import ChatOpenAI

# ========== GLM API 配置 ==========
GLM_API_KEY = "70041ddde9824461bfb02fac3f469fc3.pDZCoxOgkovIx1vT"
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 1. 自定义 GLM LLM 适配 DeepEval ==========
class GLMChatLLM(DeepEvalBaseLLM):
    """将 GLM-4-Flash 适配为 DeepEval 的 LLM 接口"""

    def __init__(self):
        self.model_name = "glm-4-flash"
        self._client = ChatOpenAI(
            model=self.model_name,
            openai_api_key=GLM_API_KEY,
            openai_api_base=GLM_BASE_URL,
            temperature=0,
        )

    def load_model(self):
        return self._client

    def generate(self, prompt: str) -> str:
        resp = self._client.invoke(prompt)
        return resp.content

    async def a_generate(self, prompt: str) -> str:
        resp = await self._client.ainvoke(prompt)
        return resp.content

    def get_model_name(self):
        return self.model_name


# ========== 2. 准备评估数据 ==========
#input: 用户问题
#actual_output: LLM 生成的回答
#retrieval_context: 检索到的文档列表
#expected_output: 标准答案（用于计算 Context Recall）
test_cases = [
    {
        "input": "什么是RAG？",
        "actual_output": "RAG（检索增强生成）是一种结合外部知识库与大语言模型的技术，通过检索相关文档来增强LLM的回答能力，减少幻觉。",
        "retrieval_context": [
            "RAG（检索增强生成）通过检索外部知识库来增强大模型的回答能力，减少幻觉。",
        ],
        "expected_output": "RAG是检索增强生成技术，通过检索外部知识库来增强大模型回答，减少幻觉。",
    },
    {
        "input": "RAG系统有哪些优化方法？",
        "actual_output": "RAG系统的优化方法包括：查询改写（HyDE、多查询改写）、混合检索（BM25+向量检索）、重排序（Cross-Encoder）、上下文压缩等。",
        "retrieval_context": [
            "RAG常见优化策略：查询改写、混合检索、重排序、上下文压缩、分块策略优化。",
            "BM25基于词频和逆文档频率，擅长关键词精确匹配。",
        ],
        "expected_output": "RAG优化方法包括查询改写、混合检索、重排序、上下文压缩、分块策略优化等。",
    },
    {
        "input": "如何选择向量数据库？",
        "actual_output": "选择向量数据库需要考虑：数据规模（FAISS适合小规模、Milvus适合大规模）、是否需要持久化、是否需要分布式、部署复杂度等因素。",
        "retrieval_context": [
            "向量数据库选型：FAISS适合本地实验，Milvus/Pinecone适合生产环境，Chroma适合轻量原型。",
        ],
        "expected_output": "向量数据库选型：FAISS适合本地实验，Milvus/Pinecone适合生产环境，Chroma适合轻量原型。",
    },
]


# ========== 3. 运行 DeepEval 评估 ==========
def run_deepeval_evaluation():
    print("=" * 60)
    print("DeepEval 评估开始")
    print("=" * 60)

    glm_llm = GLMChatLLM()

    # 创建测试用例
    cases = [] 
    for data in test_cases:
        case = LLMTestCase(
            input=data["input"],
            actual_output=data["actual_output"],
            retrieval_context=data["retrieval_context"],
            expected_output=data["expected_output"],
        )
        cases.append(case)

    # 定义评估指标（使用自定义 GLM LLM）
    #threshold 参数可以调整评估的严格程度，模型参数指定用于评估的 LLM（如果指标需要调用 LLM 进行判断）
    #0.7 是一个常见的默认值，表示评估通过的最低分数要求为 0.7（满分为 1.0）。根据实际需求可以调整这个阈值来控制评估的严格程度。
    metrics = [
        FaithfulnessMetric(threshold=0.7, model=glm_llm),
        AnswerRelevancyMetric(threshold=0.7, model=glm_llm),
        ContextualPrecisionMetric(threshold=0.7, model=glm_llm),
        ContextualRecallMetric(threshold=0.7, model=glm_llm),
    ]

    # 逐个评估
    for i, case in enumerate(cases, 1):
        print(f"\n【测试用例 {i}】")
        print(f"  问题: {case.input}")
        print(f"  回答: {case.actual_output[:60]}...")

        for metric in metrics:
            metric.measure(case) # measure 方法会计算指标分数并存储在 metric.score 中
            status = "PASS" if metric.is_successful() else "FAIL"  # 根据 threshold 判断评估结果是否通过 通俗来说就是如果分数达到或超过 0.7 就算通过，否则算失败
            print(f"  {metric.__class__.__name__}: {metric.score:.4f} [{status}]")


if __name__ == "__main__":
    run_deepeval_evaluation()
    print("\n\n[OK] DeepEval 评估演示完成！")
