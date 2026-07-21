"""
Demo1: RAGAs 璇勪及妗嗘灦
鏍稿績鎸囨爣锛欶aithfulness銆丄nswer Relevancy銆丆ontext Precision銆丆ontext Recall
娉ㄦ剰锛歊AGAs 鐗堟湰闇€涓?langchain-community 鍏煎
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from datasets import Dataset # 鐢ㄤ簬鏋勫缓璇勪及鏁版嵁闆?from ragas import evaluate # RAGAs 璇勪及鍑芥暟
from ragas.metrics import ( # RAGAs 鍐呯疆璇勪及鎸囨爣
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper # 灏?LangChain LLM 鍖呰涓?RAGAs 鍏煎鎺ュ彛
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings # LangChain Embeddings 鍩虹被
from fastembed import TextEmbedding # 鏈湴 BGE Embedding 妯″瀷

# ========== GLM API 閰嶇疆 ==========
GLM_API_KEY = __import__("os").environ.get("GLM_API_KEY")
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 1. 鍑嗗璇勪及鏁版嵁 ==========
# RAGAs 闇€瑕佷互涓嬪瓧娈碉細
# - question: 鐢ㄦ埛闂
# - answer: LLM 鐢熸垚鐨勫洖绛?# - contexts: 妫€绱㈠埌鐨勬枃妗ｅ垪琛?# - ground_truth: 鏍囧噯绛旀锛堢敤浜庤绠?Context Recall锛?
eval_data = {
    "question": [
        "浠€涔堟槸RAG锛?,
        "RAG绯荤粺鏈夊摢浜涗紭鍖栨柟娉曪紵",
        "濡備綍閫夋嫨鍚戦噺鏁版嵁搴擄紵",
    ],
    "answer": [
        "RAG锛堟绱㈠寮虹敓鎴愶級鏄竴绉嶇粨鍚堝閮ㄧ煡璇嗗簱涓庡ぇ璇█妯″瀷鐨勬妧鏈紝閫氳繃妫€绱㈢浉鍏虫枃妗ｆ潵澧炲己LLM鐨勫洖绛旇兘鍔涳紝鍑忓皯骞昏銆?,
        "RAG绯荤粺鐨勪紭鍖栨柟娉曞寘鎷細鏌ヨ鏀瑰啓锛圚yDE銆佸鏌ヨ鏀瑰啓锛夈€佹贩鍚堟绱紙BM25+鍚戦噺妫€绱級銆侀噸鎺掑簭锛圕ross-Encoder锛夈€佷笂涓嬫枃鍘嬬缉绛夈€?,
        "閫夋嫨鍚戦噺鏁版嵁搴撻渶瑕佽€冭檻锛氭暟鎹妯★紙FAISS閫傚悎灏忚妯°€丮ilvus閫傚悎澶ц妯★級銆佹槸鍚﹂渶瑕佹寔涔呭寲銆佹槸鍚﹂渶瑕佸垎甯冨紡銆侀儴缃插鏉傚害绛夊洜绱犮€?,
    ],
    "contexts": [
        ["RAG锛堟绱㈠寮虹敓鎴愶級閫氳繃妫€绱㈠閮ㄧ煡璇嗗簱鏉ュ寮哄ぇ妯″瀷鐨勫洖绛旇兘鍔涳紝鍑忓皯骞昏銆?],
        ["RAG甯歌浼樺寲绛栫暐锛氭煡璇㈡敼鍐欍€佹贩鍚堟绱€侀噸鎺掑簭銆佷笂涓嬫枃鍘嬬缉銆佸垎鍧楃瓥鐣ヤ紭鍖栥€?, "BM25鍩轰簬璇嶉鍜岄€嗘枃妗ｉ鐜囷紝鎿呴暱鍏抽敭璇嶇簿纭尮閰嶃€?],
        ["鍚戦噺鏁版嵁搴撻€夊瀷锛欶AISS閫傚悎鏈湴瀹為獙锛孧ilvus/Pinecone閫傚悎鐢熶骇鐜锛孋hroma閫傚悎杞婚噺鍘熷瀷銆?],
    ],
    "ground_truth": [
        "RAG锛圧etrieval-Augmented Generation锛夋槸妫€绱㈠寮虹敓鎴愭妧鏈紝閫氳繃妫€绱㈠閮ㄧ煡璇嗗簱鏉ュ寮哄ぇ妯″瀷鍥炵瓟锛屽噺灏戝够瑙夈€?,
        "RAG浼樺寲鏂规硶鍖呮嫭鏌ヨ鏀瑰啓銆佹贩鍚堟绱€侀噸鎺掑簭銆佷笂涓嬫枃鍘嬬缉銆佸垎鍧楃瓥鐣ヤ紭鍖栫瓑銆?,
        "鍚戦噺鏁版嵁搴撻€夊瀷锛欶AISS閫傚悎鏈湴瀹為獙锛孧ilvus/Pinecone閫傚悎鐢熶骇鐜锛孋hroma閫傚悎杞婚噺鍘熷瀷銆?,
    ],
}

dataset = Dataset.from_dict(eval_data)


# ========== 鏈湴 BGE Embedding 閫傞厤 LangChain 鎺ュ彛 ==========
class FastEmbedEmbeddings(Embeddings):
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self._model = TextEmbedding(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(v) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(list(self._model.embed([text]))[0])


# ========== 2. 閰嶇疆璇勪及鐢ㄧ殑 LLM 鍜?Embedding ==========
llm = ChatOpenAI(
    model="glm-4-flash",
    openai_api_key=GLM_API_KEY,
    openai_api_base=GLM_BASE_URL,
    temperature=0,
)

# 鐢ㄦ湰鍦?BGE 妯″瀷鏇夸唬 GLM Embedding API
embeddings = FastEmbedEmbeddings("BAAI/bge-small-zh-v1.5")

# 鍖呰涓?RAGAs 鍏煎鏍煎紡
wrapped_llm = LangchainLLMWrapper(llm)
wrapped_embeddings = LangchainEmbeddingsWrapper(embeddings)


# ========== 3. 杩愯 RAGAs 璇勪及 ==========
def run_ragas_evaluation():
    print("=" * 60)
    print("RAGAs 璇勪及寮€濮?)
    print("=" * 60)

    result = evaluate(
        dataset=dataset,
        metrics=[ # 閫夋嫨璇勪及鎸囨爣
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=wrapped_llm,
        embeddings=wrapped_embeddings,
    )

    print("\n銆愯瘎浼扮粨鏋溿€?)
    print(result)

    df = result.to_pandas() # 杞崲涓?DataFrame 浠ヤ究鏇村ソ灞曠ず鍜屽垎鏋?    print("\n銆愯缁嗙粨鏋滐紙DataFrame锛夈€?)
    print(df.to_string())

    print("\n銆愬钩鍧囧垎銆?)
    for col in df.columns:
        if df[col].dtype in ['float64', 'float32']:
            print(f"  {col}: {df[col].mean():.4f}")


if __name__ == "__main__":
    run_ragas_evaluation()
    print("\n\n[OK] RAGAs 璇勪及婕旂ず瀹屾垚锛?)

