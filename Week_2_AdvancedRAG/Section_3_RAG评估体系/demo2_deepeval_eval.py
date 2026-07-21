"""
Demo2: DeepEval 璇勪及妗嗘灦
鐗圭偣锛氭敮鎸?pytest 闆嗘垚銆丟-Eval 鑷畾涔夎瘎浼般€佹湰鍦拌瘎浼?"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from deepeval import evaluate # DeepEval 璇勪及鍑芥暟
from deepeval.test_case import LLMTestCase # DeepEval 娴嬭瘯鐢ㄤ緥绫?from deepeval.metrics import (  # DeepEval 鍐呯疆璇勪及鎸囨爣
    FaithfulnessMetric, # 璇勪及鍥炵瓟涓庢绱笂涓嬫枃鐨勪竴鑷存€?    AnswerRelevancyMetric, # 璇勪及鍥炵瓟涓庨棶棰樼殑鐩稿叧鎬?    ContextualPrecisionMetric, # 璇勪及妫€绱㈠埌鐨勪笂涓嬫枃鐨勭簿纭€?    ContextualRecallMetric, # 璇勪及妫€绱㈠埌鐨勪笂涓嬫枃鐨勫畬鏁存€?)
from deepeval.models.base_model import DeepEvalBaseLLM # DeepEval LLM 鍩虹被
from langchain_openai import ChatOpenAI

# ========== GLM API 閰嶇疆 ==========
GLM_API_KEY = __import__("os").environ.get("GLM_API_KEY")
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 1. 鑷畾涔?GLM LLM 閫傞厤 DeepEval ==========
class GLMChatLLM(DeepEvalBaseLLM):
    """灏?GLM-4-Flash 閫傞厤涓?DeepEval 鐨?LLM 鎺ュ彛"""

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


# ========== 2. 鍑嗗璇勪及鏁版嵁 ==========
#input: 鐢ㄦ埛闂
#actual_output: LLM 鐢熸垚鐨勫洖绛?#retrieval_context: 妫€绱㈠埌鐨勬枃妗ｅ垪琛?#expected_output: 鏍囧噯绛旀锛堢敤浜庤绠?Context Recall锛?test_cases = [
    {
        "input": "浠€涔堟槸RAG锛?,
        "actual_output": "RAG锛堟绱㈠寮虹敓鎴愶級鏄竴绉嶇粨鍚堝閮ㄧ煡璇嗗簱涓庡ぇ璇█妯″瀷鐨勬妧鏈紝閫氳繃妫€绱㈢浉鍏虫枃妗ｆ潵澧炲己LLM鐨勫洖绛旇兘鍔涳紝鍑忓皯骞昏銆?,
        "retrieval_context": [
            "RAG锛堟绱㈠寮虹敓鎴愶級閫氳繃妫€绱㈠閮ㄧ煡璇嗗簱鏉ュ寮哄ぇ妯″瀷鐨勫洖绛旇兘鍔涳紝鍑忓皯骞昏銆?,
        ],
        "expected_output": "RAG鏄绱㈠寮虹敓鎴愭妧鏈紝閫氳繃妫€绱㈠閮ㄧ煡璇嗗簱鏉ュ寮哄ぇ妯″瀷鍥炵瓟锛屽噺灏戝够瑙夈€?,
    },
    {
        "input": "RAG绯荤粺鏈夊摢浜涗紭鍖栨柟娉曪紵",
        "actual_output": "RAG绯荤粺鐨勪紭鍖栨柟娉曞寘鎷細鏌ヨ鏀瑰啓锛圚yDE銆佸鏌ヨ鏀瑰啓锛夈€佹贩鍚堟绱紙BM25+鍚戦噺妫€绱級銆侀噸鎺掑簭锛圕ross-Encoder锛夈€佷笂涓嬫枃鍘嬬缉绛夈€?,
        "retrieval_context": [
            "RAG甯歌浼樺寲绛栫暐锛氭煡璇㈡敼鍐欍€佹贩鍚堟绱€侀噸鎺掑簭銆佷笂涓嬫枃鍘嬬缉銆佸垎鍧楃瓥鐣ヤ紭鍖栥€?,
            "BM25鍩轰簬璇嶉鍜岄€嗘枃妗ｉ鐜囷紝鎿呴暱鍏抽敭璇嶇簿纭尮閰嶃€?,
        ],
        "expected_output": "RAG浼樺寲鏂规硶鍖呮嫭鏌ヨ鏀瑰啓銆佹贩鍚堟绱€侀噸鎺掑簭銆佷笂涓嬫枃鍘嬬缉銆佸垎鍧楃瓥鐣ヤ紭鍖栫瓑銆?,
    },
    {
        "input": "濡備綍閫夋嫨鍚戦噺鏁版嵁搴擄紵",
        "actual_output": "閫夋嫨鍚戦噺鏁版嵁搴撻渶瑕佽€冭檻锛氭暟鎹妯★紙FAISS閫傚悎灏忚妯°€丮ilvus閫傚悎澶ц妯★級銆佹槸鍚﹂渶瑕佹寔涔呭寲銆佹槸鍚﹂渶瑕佸垎甯冨紡銆侀儴缃插鏉傚害绛夊洜绱犮€?,
        "retrieval_context": [
            "鍚戦噺鏁版嵁搴撻€夊瀷锛欶AISS閫傚悎鏈湴瀹為獙锛孧ilvus/Pinecone閫傚悎鐢熶骇鐜锛孋hroma閫傚悎杞婚噺鍘熷瀷銆?,
        ],
        "expected_output": "鍚戦噺鏁版嵁搴撻€夊瀷锛欶AISS閫傚悎鏈湴瀹為獙锛孧ilvus/Pinecone閫傚悎鐢熶骇鐜锛孋hroma閫傚悎杞婚噺鍘熷瀷銆?,
    },
]


# ========== 3. 杩愯 DeepEval 璇勪及 ==========
def run_deepeval_evaluation():
    print("=" * 60)
    print("DeepEval 璇勪及寮€濮?)
    print("=" * 60)

    glm_llm = GLMChatLLM()

    # 鍒涘缓娴嬭瘯鐢ㄤ緥
    cases = [] 
    for data in test_cases:
        case = LLMTestCase(
            input=data["input"],
            actual_output=data["actual_output"],
            retrieval_context=data["retrieval_context"],
            expected_output=data["expected_output"],
        )
        cases.append(case)

    # 瀹氫箟璇勪及鎸囨爣锛堜娇鐢ㄨ嚜瀹氫箟 GLM LLM锛?    #threshold 鍙傛暟鍙互璋冩暣璇勪及鐨勪弗鏍肩▼搴︼紝妯″瀷鍙傛暟鎸囧畾鐢ㄤ簬璇勪及鐨?LLM锛堝鏋滄寚鏍囬渶瑕佽皟鐢?LLM 杩涜鍒ゆ柇锛?    #0.7 鏄竴涓父瑙佺殑榛樿鍊硷紝琛ㄧず璇勪及閫氳繃鐨勬渶浣庡垎鏁拌姹備负 0.7锛堟弧鍒嗕负 1.0锛夈€傛牴鎹疄闄呴渶姹傚彲浠ヨ皟鏁磋繖涓槇鍊兼潵鎺у埗璇勪及鐨勪弗鏍肩▼搴︺€?    metrics = [
        FaithfulnessMetric(threshold=0.7, model=glm_llm),
        AnswerRelevancyMetric(threshold=0.7, model=glm_llm),
        ContextualPrecisionMetric(threshold=0.7, model=glm_llm),
        ContextualRecallMetric(threshold=0.7, model=glm_llm),
    ]

    # 閫愪釜璇勪及
    for i, case in enumerate(cases, 1):
        print(f"\n銆愭祴璇曠敤渚?{i}銆?)
        print(f"  闂: {case.input}")
        print(f"  鍥炵瓟: {case.actual_output[:60]}...")

        for metric in metrics:
            metric.measure(case) # measure 鏂规硶浼氳绠楁寚鏍囧垎鏁板苟瀛樺偍鍦?metric.score 涓?            status = "PASS" if metric.is_successful() else "FAIL"  # 鏍规嵁 threshold 鍒ゆ柇璇勪及缁撴灉鏄惁閫氳繃 閫氫織鏉ヨ灏辨槸濡傛灉鍒嗘暟杈惧埌鎴栬秴杩?0.7 灏辩畻閫氳繃锛屽惁鍒欑畻澶辫触
            print(f"  {metric.__class__.__name__}: {metric.score:.4f} [{status}]")


if __name__ == "__main__":
    run_deepeval_evaluation()
    print("\n\n[OK] DeepEval 璇勪及婕旂ず瀹屾垚锛?)

