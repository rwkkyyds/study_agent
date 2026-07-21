"""
Demo1: HyDE锛堝亣璁炬€ф枃妗ｅ祵鍏ワ級妫€绱?鏍稿績鎬濊矾锛氳LLM鍏堢敓鎴愬亣璁炬€х瓟妗堬紝鐢ㄧ瓟妗堝幓妫€绱紝鑰屼笉鏄敤闂
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8") # 瑙ｅ喅涓枃杈撳嚭涔辩爜闂

from fastembed import TextEmbedding   # 鐢ㄤ簬鍔犺浇鏈湴 BGE 妯″瀷鐢熸垚 Embedding
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
        self._model = TextEmbedding(model_name) # 鍔犺浇鏈湴 BGE 妯″瀷

    def embed_documents(self, texts: list[str]) -> list[list[float]]:  # 杩斿洖 list[list[float]] 浠ラ€傞厤 FAISS 鐨勮緭鍏ヨ姹?        return [list(v) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(list(self._model.embed([text]))[0]) #list(self._model.embed([text]))[0] 鏄竴涓?numpy array锛岃浆鎹㈡垚 list 浠ラ€傞厤 FAISS 鐨勮緭鍏ヨ姹?

# ========== 1. 鍑嗗妯℃嫙鏂囨。搴?==========
docs = [
    Document(page_content="RAG锛堟绱㈠寮虹敓鎴愶級閫氳繃妫€绱㈠閮ㄧ煡璇嗗簱鏉ュ寮哄ぇ妯″瀷鐨勫洖绛旇兘鍔涳紝鍑忓皯骞昏銆?, metadata={"source": "rag_intro"}),
    Document(page_content="鍚戦噺鏁版嵁搴撴槸RAG绯荤粺鐨勬牳蹇冪粍浠讹紝璐熻矗瀛樺偍鍜屾绱㈡枃妗ｇ殑Embedding鍚戦噺銆?, metadata={"source": "vector_db"}),
    Document(page_content="LangChain鏄竴涓敤浜庢瀯寤篖LM搴旂敤鐨勬鏋讹紝鎻愪緵浜嗕赴瀵岀殑缁勪欢鍜岄摼寮忚皟鐢ㄨ兘鍔涖€?, metadata={"source": "langchain"}),
    Document(page_content="Embedding鏄皢鏂囨湰杞崲涓洪珮缁村悜閲忕殑鎶€鏈紝璇箟鐩歌繎鐨勬枃鏈湪鍚戦噺绌洪棿涓窛绂绘洿杩戙€?, metadata={"source": "embedding"}),
    Document(page_content="FastAPI鏄竴涓珮鎬ц兘鐨凱ython Web妗嗘灦锛屾敮鎸佸紓姝ュ鐞嗭紝閫傚悎鏋勫缓API鏈嶅姟銆?, metadata={"source": "fastapi"}),
    Document(page_content="Docker瀹瑰櫒鍖栨妧鏈彲浠ュ皢搴旂敤鍙婂叾渚濊禆鎵撳寘锛屽疄鐜扮幆澧冧竴鑷存€у拰蹇€熼儴缃层€?, metadata={"source": "docker"}),
]

# ========== 2. 鍒涘缓鍚戦噺搴擄紙鐢ㄦ湰鍦?BGE 妯″瀷锛?==========
embeddings = FastEmbedEmbeddings("BAAI/bge-small-zh-v1.5")
vectorstore = FAISS.from_documents(documents=docs, embedding=embeddings) 
# 鍒涘缓FAISS鍚戦噺搴撳苟鐢熸垚鏂囨。鐨凟mbedding,  from_documents鏂规硶浼氳皟鐢?FastEmbedEmbeddings 鐨?embed_documents 鏂规硶鏉ョ敓鎴愭枃妗ｇ殑Embedding
retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) # 鍒涘缓妫€绱㈠櫒锛岃缃瘡娆℃绱㈣繑鍥?鏉℃渶鐩稿叧鐨勬枃妗?
# ========== 3. 瀹氫箟 HyDE 閾?==========
# HyDE鏍稿績锛氬厛璁㎜LM鐢熸垚鍋囪鎬ф枃妗?hyde_prompt = ChatPromptTemplate.from_template("""
璇锋牴鎹互涓嬮棶棰橈紝鍐欎竴娈靛彲鑳藉寘鍚瓟妗堢殑鎶€鏈枃妗ｅ唴瀹癸紙绾?00瀛楋級銆?涓嶉渶瑕佸噯纭紝鍙渶瑕佺湅璧锋潵鍍忔槸鍥炵瓟杩欎釜闂鐨勬枃妗ｆ钀姐€?
闂锛歿question}

鍋囪鎬ф枃妗ｏ細
""")

llm = ChatOpenAI(
    model="glm-4-flash",
    openai_api_key=GLM_API_KEY,
    openai_api_base=GLM_BASE_URL,
    temperature=0.7,
)
hyde_chain = hyde_prompt | llm | StrOutputParser()

# ========== 4. 瀵规瘮锛氱洿鎺ユ绱?vs HyDE妫€绱?==========
def demo_comparison(question: str):
    print(f"\n{'='*60}")
    print(f"鐢ㄦ埛闂: {question}")
    print(f"{'='*60}")

    # 鏂瑰紡1: 鐩存帴鐢ㄩ棶棰樻绱?    print("\n銆愮洿鎺ユ绱€戠敤鍘熷闂:")
    direct_results = retriever.invoke(question) 
    #direct_results 鏄竴涓?list[Document]锛屾瘡涓?Document 鍖呭惈 page_content 鍜?metadata
    for i, doc in enumerate(direct_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:60]}...")

    # 鏂瑰紡2: HyDE妫€绱?    print("\n銆怘yDE妫€绱€戝厛鐢熸垚鍋囪鎬ф枃妗?")
    hypothetical_doc = hyde_chain.invoke({"question": question})
    print(f"  鍋囪鎬ф枃妗? {hypothetical_doc[:100]}...")

    hyde_results = retriever.invoke(hypothetical_doc)
    print(f"\n  鐢ㄥ亣璁炬€ф枃妗ｆ绱㈠埌:")
    for i, doc in enumerate(hyde_results, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:60]}...")

# ========== 5. 杩愯瀵规瘮 ==========
if __name__ == "__main__":
    demo_comparison("浠€涔堟槸RAG锛?)
    demo_comparison("濡備綍閮ㄧ讲LLM搴旂敤锛?)
    print("\n\n[OK] HyDE 瀵规瘮婕旂ず瀹屾垚锛?)

