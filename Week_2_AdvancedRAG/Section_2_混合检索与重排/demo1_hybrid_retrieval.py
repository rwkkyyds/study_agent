"""
Demo1: 娣峰悎妫€绱紙BM25 + 鍚戦噺妫€绱級+ RRF 铻嶅悎
鏍稿績鎬濊矾锛欱M25鎿呴暱鍏抽敭璇嶇簿纭尮閰嶏紝鍚戦噺妫€绱㈡搮闀胯涔夊尮閰嶏紝铻嶅悎鍚庢晥鏋滄渶濂?"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from fastembed import TextEmbedding
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever 
#杩欎釜鍖呯殑浣滅敤鏄?鎻愪緵BM25妫€绱㈢畻娉曠殑瀹炵幇锛屽彲浠ュ熀浜庢枃妗ｉ泦鍚堟瀯寤築M25绱㈠紩锛屽苟杩涜鍏抽敭璇嶆绱€?from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings 
#杩欎釜鍖呯殑浣滅敤鏄?瀹氫箟浜咵mbeddings绫伙紝浣滀负鏂囨湰鍚戦噺鍖栫殑鎺ュ彛瑙勮寖锛屾柟渚块€傞厤涓嶅悓鐨凟mbedding妯″瀷锛堝OpenAI銆丗astEmbed绛夛級骞跺湪绯荤粺涓粺涓€璋冪敤銆?from langchain_core.retrievers import BaseRetriever 
#杩欎釜鍖呯殑浣滅敤鏄彁渚涙绱㈠櫒鐨勫熀绫伙紝瀹氫箟浜嗘绱㈠櫒鐨勬帴鍙ｈ鑼冿紝鏂逛究瀹炵幇涓嶅悓绫诲瀷鐨勬绱㈠櫒锛堝鍚戦噺妫€绱€丅M25妫€绱㈢瓑锛夊苟鍦ㄧ郴缁熶腑缁熶竴璋冪敤銆?
# ========== GLM API 閰嶇疆 ==========
GLM_API_KEY = __import__("os").environ.get("GLM_API_KEY")
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== FastEmbed 閫傞厤 LangChain 鎺ュ彛 ==========
class FastEmbedEmbeddings(Embeddings):
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self._model = TextEmbedding(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(v) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(list(self._model.embed([text]))[0])


# ========== 1. 鍑嗗鏂囨。搴?==========
docs = [
    Document(page_content="RAG锛堟绱㈠寮虹敓鎴愶級閫氳繃妫€绱㈠閮ㄧ煡璇嗗簱鏉ュ寮哄ぇ妯″瀷鐨勫洖绛旇兘鍔涳紝鍑忓皯骞昏銆?, metadata={"source": "rag_intro.txt"}),
    Document(page_content="鍚戦噺鏁版嵁搴撴槸RAG绯荤粺鐨勬牳蹇冪粍浠讹紝璐熻矗瀛樺偍鍜屾绱㈡枃妗ｇ殑Embedding鍚戦噺銆?, metadata={"source": "vector_db.txt"}),
    Document(page_content="LangChain鏄竴涓敤浜庢瀯寤篖LM搴旂敤鐨勬鏋讹紝鎻愪緵浜嗕赴瀵岀殑缁勪欢鍜岄摼寮忚皟鐢ㄨ兘鍔涖€?, metadata={"source": "langchain.txt"}),
    Document(page_content="FastAPI鏄竴涓珮鎬ц兘鐨凱ython Web妗嗘灦锛屾敮鎸佸紓姝ュ鐞嗭紝閫傚悎鏋勫缓API鏈嶅姟銆?, metadata={"source": "fastapi.txt"}),
    Document(page_content="Docker瀹瑰櫒鍖栨妧鏈彲浠ュ皢搴旂敤鍙婂叾渚濊禆鎵撳寘锛屽疄鐜扮幆澧冧竴鑷存€у拰蹇€熼儴缃层€?, metadata={"source": "docker.txt"}),
    Document(page_content="BM25鏄竴绉嶅熀浜庤瘝棰戝拰閫嗘枃妗ｉ鐜囩殑缁忓吀妫€绱㈢畻娉曪紝鎿呴暱鍏抽敭璇嶇簿纭尮閰嶃€?, metadata={"source": "bm25.txt"}),
    Document(page_content="Embedding灏嗘枃鏈浆鎹负鍚戦噺锛岃涔夌浉杩戠殑鏂囨湰鍚戦噺璺濈鏇磋繎銆?, metadata={"source": "embedding.txt"}),
    Document(page_content="Python 3.12 寮曞叆浜?match 璇彞锛屾敮鎸佹ā寮忓尮閰嶈娉曘€?, metadata={"source": "python_match.txt"}),
    Document(page_content="Python 鐨?GIL锛堝叏灞€瑙ｉ噴鍣ㄩ攣锛夐檺鍒朵簡澶氱嚎绋嬪苟鍙戞€ц兘銆?, metadata={"source": "python_gil.txt"}),
    Document(page_content="Pydantic 鐢ㄤ簬鏁版嵁鏍￠獙锛岄€氳繃绫诲瀷娉ㄨВ鑷姩楠岃瘉杈撳叆鏁版嵁銆?, metadata={"source": "pydantic.txt"}),
]

# ========== 2. 鍒涘缓涓ょ妫€绱㈠櫒 ==========

# BM25 鍏抽敭璇嶆绱㈠櫒
bm25_retriever = BM25Retriever.from_documents(documents=docs, k=5) 

# 鍚戦噺妫€绱㈠櫒
embeddings = FastEmbedEmbeddings("BAAI/bge-small-zh-v1.5")
vectorstore = FAISS.from_documents(documents=docs, embedding=embeddings)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
#vector_retriever鏄熀浜嶧AISS鍚戦噺鏁版嵁搴撴瀯寤虹殑妫€绱㈠櫒锛宻earch_kwargs={"k": 5}琛ㄧず姣忔妫€绱㈣繑鍥炴渶鐩稿叧鐨?涓枃妗ｃ€?#杩斿洖鍊兼槸涓€涓狣ocument瀵硅薄鍒楄〃锛屾瘡涓狣ocument鍖呭惈page_content锛堟枃妗ｅ唴瀹癸級鍜宮etadata锛堟枃妗ｅ厓鏁版嵁锛屽鏉ユ簮锛夈€?

# ========== 3. RRF 铻嶅悎妫€绱?==========
def rrf_fusion(
    retriever_results: list[list[Document]],
    k: int = 60, #k鏄疪RF绠楁硶涓殑骞虫粦甯告暟锛岄€氬父鍙?0锛屽彲浠ユ牴鎹疄闄呮儏鍐佃皟鏁淬€傝緝澶х殑k鍊间細闄嶄綆鎺掑悕闈犲悗鐨勬枃妗ｇ殑褰卞搷锛岃緝灏忕殑k鍊间細澧炲姞鎺掑悕闈犲悗鐨勬枃妗ｇ殑褰卞搷銆?    top_n: int = 5,
) -> list[Document]:
    """
    RRF (Reciprocal Rank Fusion) 铻嶅悎澶氫釜妫€绱㈠櫒鐨勭粨鏋?    鍏紡: score = 危 1 / (k + rank_i)
    k: 骞虫粦甯告暟锛岄€氬父鍙?60
    """
    scores: dict[str, float] = {} 
    #scores鏄竴涓瓧鍏革紝鐢ㄤ簬瀛樺偍姣忎釜鏂囨。鐨凴RF鍒嗘暟锛宬ey鏄枃妗ｇ殑鍞竴鏍囪瘑锛堣繖閲岀敤鍐呭鍋氬幓閲峩ey锛夛紝value鏄鏂囨。鐨凴RF鍒嗘暟銆傚垵濮嬫椂姣忎釜鏂囨。鐨勫垎鏁颁负0.0銆?    doc_map: dict[str, Document] = {}
    #doc_map鏄竴涓瓧鍏革紝鐢ㄤ簬瀛樺偍鏂囨。鐨勬槧灏勫叧绯伙紝key鏄枃妗ｇ殑鍞竴鏍囪瘑锛堣繖閲岀敤鍐呭鍋氬幓閲峩ey锛夛紝value鏄搴旂殑Document瀵硅薄銆傝繖涓槧灏勫叧绯诲湪璁＄畻RRF鍒嗘暟鏃剁敤浜庡揩閫熸煡鎵綝ocument瀵硅薄銆?    for results in retriever_results: #杩欎釜鏁翠綋鐨勪綔鐢ㄦ槸瀵瑰涓绱㈠櫒鐨勭粨鏋滆繘琛岃瀺鍚堬紝璁＄畻姣忎釜鏂囨。鐨凴RF鍒嗘暟锛屽苟杩斿洖鎺掑悕鍓峵op_n鐨勬枃妗ｅ垪琛ㄣ€?        for rank, doc in enumerate(results):
            doc_id = doc.page_content  # 鐢ㄥ唴瀹瑰仛鍘婚噸key
            if doc_id not in scores:
                scores[doc_id] = 0.0
                doc_map[doc_id] = doc
            scores[doc_id] += 1.0 / (k + rank)

    # 鎸?RRF 鍒嗘暟闄嶅簭鎺掑簭
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[doc_id] for doc_id, _ in sorted_docs[:top_n]] #杩斿洖鎺掑悕鍓峵op_n鐨凞ocument瀵硅薄鍒楄〃锛宒oc_map[doc_id]鐢ㄤ簬鏍规嵁鏂囨。鍞竴鏍囪瘑鏌ユ壘瀵瑰簲鐨凞ocument瀵硅薄銆?

# ========== 4. 瀵规瘮婕旂ず ==========
def demo_comparison(question: str):
    print(f"\n{'='*60}")
    print(f"闂: {question}")
    print(f"{'='*60}")

    # BM25 妫€绱?    bm25_results = bm25_retriever.invoke(question)
    #杩斿洖鍊兼槸涓€涓狣ocument瀵硅薄鍒楄〃锛屾瘡涓狣ocument鍖呭惈page_content锛堟枃妗ｅ唴瀹癸級鍜宮etadata锛堟枃妗ｅ厓鏁版嵁锛屽鏉ユ簮锛夈€傝繖涓垪琛ㄦ槸BM25妫€绱㈠櫒鏍规嵁杈撳叆闂杩斿洖鐨勬渶鐩稿叧鐨?涓枃妗ｃ€?    print(f"\n銆怋M25 鍏抽敭璇嶆绱€慣op-5:")
    for i, doc in enumerate(bm25_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:50]}...")

    # 鍚戦噺妫€绱?    vector_results = vector_retriever.invoke(question)
    #杩斿洖鍊兼槸涓€涓狣ocument瀵硅薄鍒楄〃锛屾瘡涓狣ocument鍖呭惈page_content锛堟枃妗ｅ唴瀹癸級鍜宮etadata锛堟枃妗ｅ厓鏁版嵁锛屽鏉ユ簮锛夈€傝繖涓垪琛ㄦ槸鍚戦噺妫€绱㈠櫒鏍规嵁杈撳叆闂杩斿洖鐨勬渶鐩稿叧鐨?涓枃妗ｃ€?    print(f"\n銆愬悜閲忚涔夋绱€慣op-5:")
    for i, doc in enumerate(vector_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:50]}...")

    # RRF 娣峰悎妫€绱?    hybrid_results = rrf_fusion([bm25_results, vector_results], top_n=5)
    print(f"\n銆怰RF 娣峰悎妫€绱€慣op-5:")
    for i, doc in enumerate(hybrid_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:50]}...")


# ========== 5. 杩愯 ==========
if __name__ == "__main__":
    demo_comparison("Python 鐨?match 璇硶鎬庝箞鐢紵")
    demo_comparison("RAG 绯荤粺鎬庝箞鍑忓皯骞昏锛?)
    print("\n\n[OK] 娣峰悎妫€绱㈠姣旀紨绀哄畬鎴愶紒")

