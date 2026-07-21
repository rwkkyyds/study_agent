"""
Demo2: 澶氭煡璇㈡敼鍐欙紙Multi-Query锛夋绱?鏍稿績鎬濊矾锛氭妸涓€涓棶棰樹粠澶氫釜瑙掑害鏀瑰啓锛屽垎鍒绱紝鍚堝苟鍘婚噸缁撴灉
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from fastembed import TextEmbedding # 鐢ㄤ簬鍔犺浇鏈湴 BGE 妯″瀷鐢熸垚 Embedding
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings # 瀹氫箟閫傞厤鍣ㄧ被鐢ㄦ潵閫傞厤 FastEmbed 鐨?Embedding 杈撳嚭鍒?LangChain 鎺ュ彛

# ========== GLM API 閰嶇疆 ==========
GLM_API_KEY = __import__("os").environ.get("GLM_API_KEY")
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== FastEmbed 閫傞厤 LangChain 鎺ュ彛 ==========
class FastEmbedEmbeddings(Embeddings):
    """鐢?fastembed 鍔犺浇鏈湴 BGE 妯″瀷锛岄€傞厤 LangChain Embeddings 鎺ュ彛"""

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self._model = TextEmbedding(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(v) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(list(self._model.embed([text]))[0])


# ========== 1. 鍑嗗鏂囨。搴擄紙姣攄emo1鏇村鏍峰寲锛?==========
docs = [
    Document(page_content="RAG閫氳繃妫€绱㈠閮ㄧ煡璇嗘潵澧炲己LLM鍥炵瓟锛屾牳蹇冪粍浠跺寘鎷細鏂囨。鍔犺浇銆佹枃鏈垎鍧椼€丒mbedding銆佸悜閲忓簱銆佹绱㈠櫒銆丩LM銆?, metadata={"source": "rag_arch"}),
    Document(page_content="鍚戦噺鏁版嵁搴撻€夊瀷锛欶AISS閫傚悎鏈湴瀹為獙锛孧ilvus/Pinecone閫傚悎鐢熶骇鐜锛孋hroma閫傚悎杞婚噺鍘熷瀷銆?, metadata={"source": "vector_db_compare"}),
    Document(page_content="RAG甯歌浼樺寲绛栫暐锛氭煡璇㈡敼鍐欍€佹贩鍚堟绱€侀噸鎺掑簭銆佷笂涓嬫枃鍘嬬缉銆佸垎鍧楃瓥鐣ヤ紭鍖栥€?, metadata={"source": "rag_optimization"}),
    Document(page_content="Embedding妯″瀷閫夊瀷锛歄penAI text-embedding-3-small鎬т环姣旈珮锛孊GE绯诲垪鏀寔涓枃鏇村ソ銆?, metadata={"source": "embedding_model"}),
    Document(page_content="RAG璇勪及鎸囨爣锛欶aithfulness锛堝繝瀹炲害锛夈€丄nswer Relevancy锛堢瓟妗堢浉鍏虫€э級銆丆ontext Precision锛堜笂涓嬫枃绮剧‘搴︼級銆?, metadata={"source": "rag_eval"}),
    Document(page_content="LangChain LCEL閾惧紡璋冪敤锛氱敤 | 绠￠亾绗﹁繛鎺ョ粍浠讹紝鏀寔娴佸紡杈撳嚭銆佹壒閲忓鐞嗐€佸紓姝ヨ皟鐢ㄣ€?, metadata={"source": "lcel"}),
    Document(page_content="FastAPI寮傛浼樺娍锛歛sync/await骞跺彂澶勭悊璇锋眰锛岄€傚悎I/O瀵嗛泦鍨嬬殑LLM璋冪敤鍦烘櫙銆?, metadata={"source": "fastapi_async"}),
    Document(page_content="Docker澶氶樁娈垫瀯寤猴細绗竴闃舵缂栬瘧渚濊禆锛岀浜岄樁娈靛鍒朵骇鐗╋紝鍑忓皬闀滃儚浣撶Н銆?, metadata={"source": "docker_multi_stage"}),
]

# ========== 2. 鍒涘缓鍚戦噺搴擄紙鐢ㄦ湰鍦?BGE 妯″瀷锛?==========
embeddings = FastEmbedEmbeddings("BAAI/bge-small-zh-v1.5")
vectorstore = FAISS.from_documents(documents=docs, embedding=embeddings) 
# vecctorstore 鏄?涓€涓?FAISS 鍚戦噺搴撳璞★紝宸茬粡鍖呭惈浜嗘枃妗ｇ殑Embedding
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# ========== 3. 瀹氫箟澶氭煡璇㈡敼鍐欓摼 ==========
multi_query_prompt = ChatPromptTemplate.from_template("""
浣犳槸涓€涓狝I鍔╂墜锛屾搮闀夸粠涓嶅悓瑙掑害鐞嗚В鐢ㄦ埛闂銆?璇峰皢浠ヤ笅闂鏀瑰啓鎴?涓笉鍚岃搴︾殑瀛愰棶棰橈紝姣忎釜瀛愰棶棰樺崟鐙竴琛岋紝涓嶈缂栧彿銆?
鍘熷闂锛歿question}

鏀瑰啓鍚庣殑3涓瓙闂锛?""")

llm = ChatOpenAI(
    model="glm-4-flash",
    openai_api_key=GLM_API_KEY,
    openai_api_base=GLM_BASE_URL,
    temperature=0.7,
)
multi_query_chain = multi_query_prompt | llm | StrOutputParser()

# ========== 4. 澶氭煡璇㈡绱?+ 鍘婚噸 ==========
def multi_query_retrieval(question: str):
    print(f"\n{'='*60}")
    print(f"鍘熷闂: {question}")
    print(f"{'='*60}")

    # Step1: 鐢熸垚澶氫釜瀛愰棶棰?    raw_output = multi_query_chain.invoke({"question": question}) #raw_output 鏄?LLM 鐢熸垚鐨勬枃鏈紝鍖呭惈3涓瓙闂锛屾瘡涓瓙闂鍗犱竴琛?    sub_questions = [q.strip() for q in raw_output.strip().split("\n") if q.strip()]

    print(f"\n銆怱tep1銆戞敼鍐欏悗鐨勫瓙闂:")
    for i, q in enumerate(sub_questions, 1):
        print(f"  Q{i}: {q}")

    # Step2: 姣忎釜瀛愰棶棰樺垎鍒绱?    all_docs = []
    print(f"\n銆怱tep2銆戝垎鍒绱?")
    for i, q in enumerate(sub_questions, 1):
        results = retriever.invoke(q) #results 鏄竴涓?list[Document]锛屾瘡涓?Document 鍖呭惈 page_content 鍜?metadata
        print(f"  Q{i} 妫€绱㈠埌 {len(results)} 涓枃妗?)
        all_docs.extend(results)

    # Step3: 鍘婚噸锛堝熀浜巔age_content锛?    seen = set()
    unique_docs = []
    for doc in all_docs:
        content_hash = hash(doc.page_content)
        if content_hash not in seen: # -O(1) 鐨勫幓閲嶆晥鐜?            seen.add(content_hash)
            unique_docs.append(doc) # unique_docs 鏄幓閲嶅悗鐨勬枃妗ｅ垪琛?
    print(f"\n銆怱tep3銆戝悎骞跺幓閲嶇粨鏋滐紙鍏眥len(unique_docs)}涓級:")
    for i, doc in enumerate(unique_docs, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:70]}...")

    return unique_docs # 杩斿洖鏈€缁堢殑鍘婚噸鏂囨。鍒楄〃

# ========== 5. 瀵规瘮锛氬崟鏌ヨ vs 澶氭煡璇?==========
def demo_comparison(question: str):
    print(f"\n{'#'*60}")
    print(f"# 瀵规瘮婕旂ず")
    print(f"{'#'*60}")

    # 鍗曟煡璇?    print(f"\n銆愬崟鏌ヨ妫€绱€戠洿鎺ョ敤鍘熷闂:")
    single_results = retriever.invoke(question)
    for i, doc in enumerate(single_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:70]}...")
    print(f"  鍛戒腑鏂囨。鏁? {len(single_results)}")

    # 澶氭煡璇?    multi_results = multi_query_retrieval(question)
    print(f"\n  鏈€缁堝懡涓枃妗ｆ暟: {len(multi_results)}")

# ========== 6. 杩愯 ==========
if __name__ == "__main__":
    demo_comparison("RAG绯荤粺鏈夊摢浜涗紭鍖栨柟娉曪紵")
    print("\n\n[OK] 澶氭煡璇㈡敼鍐欐紨绀哄畬鎴愶紒")

