"""
Demo2: Milvus + LangChain RAG 闆嗘垚锛堟墜鍐?VectorStore 閫傞厤鍣級
鍔熻兘锛氭枃妗ｅ垎鍧?鈫?Embedding 鈫?瀛樺叆 Milvus 鈫?LangChain 妫€绱㈤摼 鈫?GLM 鍥炵瓟
鏁版嵁娴侊細Documents 鈫?bge-small-zh Embedding 鈫?Milvus 鈫?Retriever 鈫?Prompt 鈫?GLM 鈫?鍥炵瓟
渚濊禆锛歱ip install pymilvus langchain langchain-community langchain-openai fastembed
鍓嶆彁锛歞ocker compose up -d 鍚姩 Milvus 鏈嶅姟
瀛︿範浠峰€硷細鐞嗚В LangChain VectorStore 鎺ュ彛鐨勬湰璐紙灏辨槸涓€涓甫 search 鐨勫瓨鍌級
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from typing import Any
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from fastembed import TextEmbedding
from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema


# ========== 閰嶇疆 ==========
MILVUS_URI = "http://localhost:19530"
COLLECTION_NAME = "demo_rag_langchain"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
VECTOR_DIM = 512
ZHIPU_API_KEY = __import__("os").environ.get("ZHIPU_API_KEY")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 1. FastEmbed 閫傞厤鍣紙灏佽涓?LangChain Embeddings 鎺ュ彛锛?==========
class FastEmbedEmbeddings(Embeddings):
    """
    灏?fastembed 灏佽涓?LangChain 鐨?Embeddings 鎺ュ彛銆?    LangChain 瑕佹眰瀹炵幇涓や釜鏂规硶锛?    - embed_documents(texts): 鎵归噺宓屽叆鏂囨。
    - embed_query(text): 宓屽叆鍗曟潯鏌ヨ
    """
    def __init__(self, model_name: str):
        super().__init__()
        self.model = TextEmbedding(model_name)
        print(f"[OK] Embedding 妯″瀷宸插姞杞? {model_name}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = list(self.model.embed(texts))
        return [list(v) for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        return list(list(self.model.embed([text]))[0]) 
        #eg: self.model.embed([text]) 杩斿洖 [[vector]]锛岄渶瑕佸彇绗竴琛?[0]锛屽啀杞垚 list
        #鍏蜂綋渚嬪瓙: self.model.embed(["hello"]) 杩斿洖 [[0.1, 0.2, ...]]锛岄渶瑕佸彇绗竴琛?[0]锛屽啀杞垚 list 
        #[0]涓嶄篃鏄暟缁勶紵
        # 鏄殑锛宻elf.model.embed(["hello"]) 杩斿洖 [[0.1, 0.2, ...]]锛?        # 杩欐槸涓€涓簩缁存暟缁勩€傚彇绗竴琛?[0] 鍚庡緱鍒?[0.1, 0.2, ...]锛岃繖鏄竴涓竴缁存暟缁勩€傛渶鍚庡啀杞垚 list 灏辨槸鏈€缁堢殑鍚戦噺鍒楄〃銆?

# ========== 2. Milvus VectorStore 閫傞厤鍣?==========
class MilvusVectorStore(VectorStore):
    """
    鎵嬪啓 Milvus 鍚戦噺瀛樺偍閫傞厤鍣紝瀹炵幇 LangChain VectorStore 鎺ュ彛銆?    鍙渶瀹炵幇涓や釜鏍稿績鏂规硶锛?    - from_texts(): 浠庢枃鏈垱寤哄悜閲忓簱锛堝寘鎷垱寤?Collection銆佺储寮曘€佹彃鍏ユ暟鎹級
    - similarity_search(): 鐩镐技搴︽悳绱?
    杩欏睍绀轰簡 LangChain VectorStore 鐨勬湰璐細涓€涓甫 search 鎺ュ彛鐨勫瓨鍌ㄣ€?    """
    def __init__(self, client: MilvusClient, collection_name: str, embedding: Embeddings):
        self.client = client
        self.collection_name = collection_name
        self.embedding = embedding

    @classmethod
    def from_texts(
        cls,
        texts: list[str],
        embedding: Embeddings,
        metadatas: list[dict] | None = None,
        collection_name: str = "default",
        **kwargs: Any,
    ) -> "MilvusVectorStore":
        """浠庢枃鏈垪琛ㄥ垱寤哄悜閲忓簱锛圠angChain 鏍囧噯鎺ュ彛锛?""
        client = MilvusClient(uri=kwargs.get("uri", MILVUS_URI))

        # 娓呯悊鏃?Collection
        if client.has_collection(collection_name):
            client.drop_collection(collection_name)

        # 鍒涘缓 Schema
        schema = CollectionSchema(fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ])

        client.create_collection(collection_name=collection_name, schema=schema)

        # 鍒涘缓 HNSW 绱㈠紩
        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector", #鎸囧畾鍚戦噺瀛楁
            index_type="HNSW",
            metric_type="COSINE", #鎸囧畾浣跨敤浣欏鸡鐩镐技搴﹁繘琛屾悳绱?            params={"M": 16, "efConstruction": 200}, # M 鎺у埗绱㈠紩澶嶆潅搴︼紝efConstruction 鎺у埗鏋勫缓璐ㄩ噺
        )
        client.create_index(collection_name=collection_name, index_params=index_params)

        # 鍚戦噺鍖栧苟鎻掑叆
        vectors = embedding.embed_documents(texts)
        if metadatas is None:
            metadatas = [{}] * len(texts)

        data = [
            {"text": t, "vector": v, "metadata": m}
            for t, v, m in zip(texts, vectors, metadatas)
        ]
        client.insert(collection_name=collection_name, data=data)

        # 鍔犺浇鍒板唴瀛?        client.load_collection(collection_name)

        print(f"[OK] 宸插垱寤?MilvusVectorStore: {collection_name}, {len(texts)} 鏉℃枃妗?)
        return cls(client=client, collection_name=collection_name, embedding=embedding)

    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> list[Document]:
        """鐩镐技搴︽悳绱紙LangChain 鏍囧噯鎺ュ彛锛?""
        query_vector = self.embedding.embed_query(query)
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=k,
            output_fields=["text", "metadata"],
            search_params={"metric_type": "COSINE"}, #鎸囧畾浣跨敤浣欏鸡鐩镐技搴﹁繘琛屾悳绱?        )
        docs = []
        for hit in results[0]:
            docs.append(Document(
                page_content=hit["entity"]["text"],
                metadata=hit["entity"].get("metadata", {}),
            ))
        return docs

    def add_texts(self, texts: list[str], metadatas: list[dict] | None = None, **kwargs: Any) -> list[str]:
        """杩藉姞鏂囨湰锛圠angChain 鏍囧噯鎺ュ彛锛?""
        vectors = self.embedding.embed_documents(texts)
        if metadatas is None:
            metadatas = [{}] * len(texts)   # [{}, {}, {}]
        data = [
            {"text": t, "vector": v, "metadata": m}
            for t, v, m in zip(texts, vectors, metadatas)
        ]
        result = self.client.insert(collection_name=self.collection_name, data=data)
        return result["ids"] 


# ========== 3. 鍑嗗鐭ヨ瘑鏂囨。 ==========
def prepare_documents() -> tuple[list[str], list[dict]]:
    """妯℃嫙 RAG 鍦烘櫙锛氬噯澶囦竴鎵圭煡璇嗘枃妗?""
    texts = [
        "RAG锛堟绱㈠寮虹敓鎴愶級鏄綋鍓嶆渶涓绘祦鐨?LLM 搴旂敤鏋舵瀯銆傚畠閫氳繃妫€绱㈠閮ㄧ煡璇嗗簱锛屽皢鐩稿叧淇℃伅娉ㄥ叆 Prompt锛岃澶фā鍨嬪熀浜庣湡瀹炴暟鎹洖绛旓紝澶у箙鍑忓皯骞昏銆?,
        "HyDE锛堝亣璁炬枃妗ｅ祵鍏ワ級鏄竴绉嶆煡璇㈡敼鍐欐妧鏈€傚厛璁?LLM 鐢熸垚鍋囪鎬у洖绛旓紝鐢ㄥ洖绛旂殑鍚戦噺鍘绘绱㈢湡瀹炴枃妗ｏ紝鍥犱负鍋囪鍥炵瓟鍜岀湡瀹炴枃妗ｅ湪璇箟绌洪棿鏇存帴杩戙€?,
        "澶氭煡璇㈡敼鍐欙紙Multi-Query锛夎 LLM 浠庝笉鍚岃搴︾敓鎴愬涓煡璇㈠彉浣擄紝鍒嗗埆妫€绱㈠悗鍚堝苟鍘婚噸锛岃兘瑕嗙洊鏇村鐩稿叧鏂囨。銆?,
        "BM25 鏄粡鍏哥殑绋€鐤忔绱㈢畻娉曪紝鍩轰簬璇嶉鍜岄€嗘枃妗ｉ鐜囪绠楃浉鍏虫€с€傛搮闀跨簿纭叧閿瘝鍖归厤锛屼絾涓嶇悊瑙ｈ涔夈€?,
        "FAISS 鏄?Facebook 寮€婧愮殑鍚戦噺妫€绱㈠簱锛屾敮鎸佸绉嶇储寮曠被鍨嬨€傞€傚悎鐧句竾鍒板崈涓囩骇鍚戦噺鐨勬湰鍦版绱紝浣嗘病鏈夋寔涔呭寲鍜屽垎甯冨紡鑳藉姏銆?,
        "Milvus 鏄敓浜х骇鍚戦噺鏁版嵁搴擄紝鏀寔鍗佷嚎绾у悜閲忓瓨鍌ㄣ€佸垎甯冨紡閮ㄧ讲銆佸绉熸埛銆傞€傚悎浼佷笟绾?RAG 绯荤粺鐨勭敓浜ч儴缃层€?,
        "Chroma 鏄交閲忕骇鍚戦噺鏁版嵁搴擄紝API 绠€娲侊紝閫傚悎蹇€熷師鍨嬪紑鍙戙€備絾鎬ц兘鍜岃妯℃湁闄愶紝涓嶉€傚悎鐢熶骇鐜銆?,
        "ReAct锛圧easoning + Acting锛夋槸 Agent 鐨勬牳蹇冭寖寮忋€侺LM 浜ゆ浛杩涜鎺ㄧ悊鍜岃鍔紝瑙傚療缁撴灉鍚庣户缁帹鐞嗭紝鐩村埌寰楀嚭鏈€缁堢瓟妗堛€?,
        "Function Calling 鏄?OpenAI 鎻愬嚭鐨勫伐鍏疯皟鐢ㄦ満鍒躲€侺LM 杈撳嚭缁撴瀯鍖栫殑鍑芥暟璋冪敤鍙傛暟锛岀敱澶栭儴浠ｇ爜鎵ц鍚庡皢缁撴灉杩斿洖 LLM銆?,
        "Agent Memory 鍖呮嫭鐭湡璁板繂锛堝璇濅笂涓嬫枃锛夊拰闀挎湡璁板繂锛堝悜閲忔暟鎹簱瀛樺偍鐨勫巻鍙茬煡璇嗭級銆?,
    ]
    metadatas = [
        {"source": "rag", "topic": "RAG姒傝堪"},
        {"source": "rag", "topic": "HyDE"},
        {"source": "rag", "topic": "Multi-Query"},
        {"source": "rag", "topic": "BM25"},
        {"source": "vector_db", "topic": "FAISS"},
        {"source": "vector_db", "topic": "Milvus"},
        {"source": "vector_db", "topic": "Chroma"},
        {"source": "agent", "topic": "ReAct"},
        {"source": "agent", "topic": "Function Calling"},
        {"source": "agent", "topic": "Memory"},
    ]
    print(f"[OK] 宸插噯澶?{len(texts)} 绡囩煡璇嗘枃妗?)
    return texts, metadatas


# ========== 4. 鏋勫缓 RAG 妫€绱㈤摼 ==========
def build_rag_chain(vectorstore: MilvusVectorStore):
    """
    鏋勫缓 LangChain RAG 閾撅細
    Retriever 鈫?鏍煎紡鍖栦笂涓嬫枃 鈫?Prompt 鈫?GLM 鈫?瑙ｆ瀽杈撳嚭
    """
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) 
    #as_retriever() 鏄?LangChain VectorStore 鐨勬柟娉曪紝杩斿洖涓€涓?Retriever 瀵硅薄锛宻earch_kwargs={"k": 3} 鎸囧畾姣忔妫€绱㈣繑鍥?3 鏉＄浉鍏虫枃妗?
    prompt = ChatPromptTemplate.from_template(
        "浣犳槸涓€涓笓涓氱殑鎶€鏈姪鎵嬨€傝鏍规嵁浠ヤ笅鍙傝€冭祫鏂欏洖绛旂敤鎴烽棶棰樸€俓n"
        "濡傛灉鍙傝€冭祫鏂欎腑娌℃湁鐩稿叧淇℃伅锛岃鏄庣‘璇存槑'鏍规嵁宸叉湁鐭ヨ瘑鏃犳硶鍥炵瓟'銆俓n\n"
        "鍙傝€冭祫鏂?\n{context}\n\n"
        "鐢ㄦ埛闂: {question}\n\n"
        "璇风敤涓枃鍥炵瓟锛?
    )

    llm = ChatOpenAI(
        api_key=ZHIPU_API_KEY,
        base_url=ZHIPU_BASE_URL,
        model="glm-4-flash",
        temperature=0.7,
    )

    def format_docs(docs): #杩斿洖鍊?鏄竴涓瓧绗︿覆锛屾牸寮忓寲鍚庣殑鏂囨。鍐呭
        formatted = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "unknown")
            topic = doc.metadata.get("topic", "")
            formatted.append(f"[鏂囨。{i+1}] (鏉ユ簮: {source}, 涓婚: {topic})\n{doc.page_content}")
        return "\n\n".join(formatted)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )  #鏋勫缓閾捐矾锛氬厛妫€绱㈠緱鍒扮浉鍏虫枃妗ｏ紝鏍煎紡鍖栨垚瀛楃涓插悗濉叆 Prompt锛屽啀璋冪敤 LLM 鐢熸垚鍥炵瓟锛屾渶鍚庤В鏋愭垚绾枃鏈緭鍑?
    print("[OK] RAG 妫€绱㈤摼鏋勫缓瀹屾垚")
    print("     閾捐矾: 鐢ㄦ埛闂 鈫?Milvus妫€绱op-3 鈫?Prompt 鈫?GLM-4-Flash 鈫?鍥炵瓟")
    return rag_chain, retriever


# ========== 5. 绔埌绔棶绛旀祴璇?==========
def run_qa_test(rag_chain, retriever):
    """娴嬭瘯 RAG 闂瓟鏁堟灉"""
    questions = [
        "浠€涔堟槸 RAG锛熷畠瑙ｅ喅浜嗕粈涔堥棶棰橈紵",
        "Milvus 鍜?FAISS 鏈変粈涔堝尯鍒紵",
        "Agent 鐨?ReAct 鑼冨紡鏄粈涔堬紵",
        "閲忓瓙璁＄畻鐨勫師鐞嗘槸浠€涔堬紵",  # 瓒呭嚭鐭ヨ瘑搴撹寖鍥?    ]

    for i, question in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"闂 {i+1}: {question}")
        print(f"{'=' * 60}")

        docs = retriever.invoke(question) #.invoke() 鏄?LangChain Retriever 鐨勬柟娉曪紝鎵ц妫€绱㈠苟杩斿洖鐩稿叧鏂囨。鍒楄〃
        print(f"妫€绱㈠埌 {len(docs)} 绡囩浉鍏虫枃妗?")
        for j, doc in enumerate(docs):
            print(f"  [{j+1}] ({doc.metadata.get('topic', '?')}) {doc.page_content[:60]}...")

        print(f"\nGLM 鍥炵瓟:")
        answer = rag_chain.invoke(question) 
        #杩欓噷鏂硅繘鍘荤殑涓轰粈涔堜笉鏄绱㈠悗鐨刣ocs锛?        #鍥犱负rag_chain鏄痓uild_rag_chain()鍑芥暟涓瀯寤虹殑閾捐矾锛?        # 閾捐矾涓凡缁忓寘鍚簡retriever锛屾墍浠ョ洿鎺ヨ皟鐢╮ag_chain.invoke(question)灏变細鑷姩鍏堟墽琛屾绱紝寰楀埌鐩稿叧鏂囨。锛屽啀鏍煎紡鍖栨枃妗ｅ唴瀹癸紝濉叆Prompt锛屾渶鍚庤皟鐢↙LM鐢熸垚鍥炵瓟銆?        print(f"  {answer}")


# ========== 涓诲嚱鏁?==========
if __name__ == "__main__":
    try:
        # Step 1: 鍑嗗鏂囨。
        texts, metadatas = prepare_documents()

        # Step 2: 鍒濆鍖?Embedding
        embeddings = FastEmbedEmbeddings(EMBEDDING_MODEL)

        # Step 3: 鍒涘缓 Milvus 鍚戦噺搴?  
        vectorstore = MilvusVectorStore.from_texts(
            texts=texts,
            embedding=embeddings,
            metadatas=metadatas,
            collection_name=COLLECTION_NAME,
            uri=MILVUS_URI,
        )

        # Step 4: 鏋勫缓 RAG 閾?        rag_chain, retriever = build_rag_chain(vectorstore)

        # Step 5: 闂瓟娴嬭瘯
        run_qa_test(rag_chain, retriever)

        print(f"\n{'=' * 60}")
        print("[OK] Milvus + LangChain RAG 闆嗘垚婕旂ず瀹屾垚锛?)
        print("鏍稿績鏀惰幏锛?)
        print("  1. VectorStore 鎺ュ彛鐨勬湰璐?= 瀛樺偍 + 鎼滅储")
        print("  2. Milvus 鏇夸唬 FAISS锛屾敮鎸佺敓浜х骇閮ㄧ讲")
        print("  3. 鏁翠釜 RAG 閾捐矾锛氭枃妗?鈫?鍚戦噺鍖?鈫?Milvus 鈫?妫€绱?鈫?LLM")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        print("[INFO] 璇风‘淇?Milvus 鏈嶅姟宸插惎鍔紙docker compose up -d锛?)

