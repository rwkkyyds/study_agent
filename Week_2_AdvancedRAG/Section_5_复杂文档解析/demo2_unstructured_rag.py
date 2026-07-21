"""
Demo2: 澶嶆潅鏂囨。瑙ｆ瀽 + RAG 闆嗘垚
鍔熻兘锛歅DF瑙ｆ瀽(鎸夊厓绱犵被鍨? 鈫?琛ㄦ牸/鏂囨湰鍒嗙 鈫?鍒嗗潡 鈫?Milvus 鈫?RAG闂瓟
鏍稿績锛氳〃鏍兼暣浣撲繚鐣欎笉鍒囩锛岃浆Markdown渚汱LM鐞嗚В
渚濊禆锛歱ip install reportlab pdfplumber pymilvus fastembed langchain-openai
鍓嶆彁锛歞ocker compose up -d 鍚姩 Milvus 鏈嶅姟
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

import pdfplumber
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
DEMO_DIR = Path(__file__).parent / "demo_files"
PDF_PATH = DEMO_DIR / "sample_rag_doc.pdf"
MILVUS_URI = "http://localhost:19530"
COLLECTION_NAME = "demo_rag_parsed_doc"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
VECTOR_DIM = 512
ZHIPU_API_KEY = __import__("os").environ.get("ZHIPU_API_KEY")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


# ========== 鍏冪礌绫诲瀷 ==========
@dataclass
class Element:
    text: str
    metadata: dict = field(default_factory=dict)

@dataclass
class Title(Element): pass
@dataclass
class NarrativeText(Element): pass
@dataclass
class Table(Element):
    html: str = ""
@dataclass
class ListItem(Element): pass


# ========== 1. PDF 鎸夊厓绱犵被鍨嬭В鏋?==========
def partition_pdf(filename: str) -> list[Element]:
    """鎸夊厓绱犵被鍨嬭В鏋?PDF锛堝鏍?Unstructured partition_pdf锛?""
    elements = []
    with pdfplumber.open(filename) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                lines = text.split("\n")
                current_block = []
                current_type = "text"
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.endswith("锛?) or line.endswith(":") or line.startswith(("涓€銆?, "浜屻€?, "涓夈€?)):
                        new_type = "heading"
                    elif any(line.startswith(f"{i}.") for i in range(1, 10)):
                        new_type = "list"
                    else:
                        new_type = "text"
                    if new_type != current_type and current_block:
                        elements.append(_make_elem(current_type, "\n".join(current_block), page_num))
                        current_block = []
                    current_type = new_type
                    current_block.append(line)
                if current_block:
                    elements.append(_make_elem(current_type, "\n".join(current_block), page_num))

            tables = page.extract_tables()
            for table_data in tables:
                if table_data and len(table_data) > 1:
                    md = _table_to_md(table_data)
                    html = _table_to_html(table_data)
                    elements.append(Table(text=md, html=html,
                                          metadata={"page": page_num + 1, "is_table": True}))
    return elements

def _make_elem(t, text, page):
    m = {"page": page + 1}
    if t == "heading": return Title(text=text, metadata=m)
    if t == "list": return ListItem(text=text, metadata=m)
    return NarrativeText(text=text, metadata=m)

def _table_to_md(table):
    h = table[0]
    lines = ["| " + " | ".join(str(x) if x else "" for x in h) + " |"]
    lines.append("| " + " | ".join(["---"] * len(h)) + " |")
    for row in table[1:]:
        lines.append("| " + " | ".join(str(x) if x else "" for x in row) + " |")
    return "\n".join(lines)

def _table_to_html(table):
    html = ["<table><tr>" + "".join(f"<th>{h}</th>" for h in table[0]) + "</tr>"]
    for row in table[1:]:
        html.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
    html.append("</table>")
    return "\n".join(html)


# ========== 2. 鍏冪礌杞?RAG 鏂囨。 ==========
def elements_to_documents(elements: list[Element]) -> list[Document]:
    """灏嗚В鏋愬厓绱犺浆涓?LangChain Document锛岃〃鏍兼暣浣撲繚鐣?""
    docs = []
    for elem in elements:
        content = elem.text
        metadata = {**elem.metadata, "type": type(elem).__name__}
        if isinstance(elem, Table):
            content = f"[琛ㄦ牸鏁版嵁]\n{content}\n[琛ㄦ牸缁撴潫]"
        docs.append(Document(page_content=content, metadata=metadata))
    print(f"[OK] 宸插噯澶?{len(docs)} 涓?RAG 鏂囨。")
    return docs


# ========== 3. Embedding + VectorStore ==========
class FastEmbedEmbeddings(Embeddings):   #灏佽 FastEmbed 鐨勬枃鏈祵鍏ユ帴鍙ｏ紝閫傞厤 LangChain Embeddings 鎺ュ彛
    def __init__(self, model_name):
        super().__init__()
        self.model = TextEmbedding(model_name)
    def embed_documents(self, texts):
        return [list(v) for v in self.model.embed(texts)] #杩斿洖涓€涓簩缁村垪琛紝姣忎釜瀛愬垪琛ㄦ槸瀵瑰簲鏂囨湰鐨勫悜閲忚〃绀?    def embed_query(self, text):
        return list(list(self.model.embed([text]))[0]) #杩斿洖涓€涓竴缁村垪琛紝鏄煡璇㈡枃鏈殑鍚戦噺琛ㄧず

class MilvusVectorStore(VectorStore):  # 灏佽 Milvus 鍚戦噺搴撶殑鎺ュ彛锛岄€傞厤 LangChain VectorStore 鎺ュ彛 鏈塧s_retriever鏂规硶鍙互鐩存帴杞负 LangChain Retriever鎺ュ彛
    def __init__(self, client, collection_name, embedding):
        self.client = client
        self.collection_name = collection_name
        self.embedding = embedding

    @classmethod
    def from_texts(cls, texts, embedding, metadatas=None, collection_name="default", **kwargs): 
        #鏍规嵁鏂囨湰鍒楄〃鍒涘缓 Milvus 鍚戦噺搴撳疄渚嬶紝鍏堝垱寤洪泦鍚堝拰绱㈠紩锛屽啀鎵归噺鎻掑叆鏁版嵁
        client = MilvusClient(uri=kwargs.get("uri", MILVUS_URI))
        if client.has_collection(collection_name):
            client.drop_collection(collection_name)
        schema = CollectionSchema(fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ])
        client.create_collection(collection_name=collection_name, schema=schema)
        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="HNSW", metric_type="COSINE",
                               params={"M": 16, "efConstruction": 200})
        client.create_index(collection_name=collection_name, index_params=index_params)
        if metadatas is None:
            metadatas = [{}] * len(texts)
        vectors = embedding.embed_documents(texts)
        data = [{"text": t, "vector": v, "metadata": m} for t, v, m in zip(texts, vectors, metadatas)]
        client.insert(collection_name=collection_name, data=data)
        client.load_collection(collection_name)
        print(f"[OK] Milvus 鍚戦噺搴撳氨缁? {collection_name}, {len(texts)} 鏉?)
        return cls(client=client, collection_name=collection_name, embedding=embedding)

    @classmethod
    def from_documents(cls, documents, embedding, collection_name="default", **kwargs):
        client = MilvusClient(uri=kwargs.get("uri", MILVUS_URI))
        if client.has_collection(collection_name):
            client.drop_collection(collection_name)
        schema = CollectionSchema(fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ])
        client.create_collection(collection_name=collection_name, schema=schema)
        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="HNSW", metric_type="COSINE",
                               params={"M": 16, "efConstruction": 200})
        client.create_index(collection_name=collection_name, index_params=index_params)
        texts = [d.page_content for d in documents]
        metadatas = [d.metadata for d in documents]
        vectors = embedding.embed_documents(texts)
        data = [{"text": t, "vector": v, "metadata": m} for t, v, m in zip(texts, vectors, metadatas)]
        client.insert(collection_name=collection_name, data=data)
        client.load_collection(collection_name)
        print(f"[OK] Milvus 鍚戦噺搴撳氨缁? {collection_name}, {len(documents)} 鏉?)
        return cls(client=client, collection_name=collection_name, embedding=embedding) 
        #杩斿洖鐨勬槸涓€涓?MilvusVectorStore 瀹炰緥锛屽皝瑁呬簡 Milvus 鐨勬绱㈡帴鍙? 鏈塧s_retriever鏂规硶鍙互鐩存帴杞负 LangChain Retriever鎺ュ彛

    def similarity_search(self, query, k=4, **kwargs):
        qv = self.embedding.embed_query(query)
        results = self.client.search(collection_name=self.collection_name, data=[qv], limit=k,
                                     output_fields=["text", "metadata"],
                                     search_params={"metric_type": "COSINE"})
        return [Document(page_content=hit["entity"]["text"],
                         metadata=hit["entity"].get("metadata", {})) for hit in results[0]]


# ========== 4. RAG 閾捐矾 ==========
def build_rag_chain(vectorstore):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) #杩斿洖鏍煎紡 eg: [Document(page_content='[琛ㄦ牸鏁版嵁]\n| 鍚戦噺鏁版嵁搴?| 閫傜敤鍦烘櫙 |\n| --- | --- |\n| Milvus | 澶ц妯″悜閲忔绱?|\n| FAISS | 鏈湴灏忚妯℃绱?|\n[琛ㄦ牸缁撴潫]', metadata={'page': 2, 'type': 'Table'})]
    #杩斿洖涓€涓?Retriever 瀹炰緥锛屽皝瑁呬簡 Milvus 鐨勬绱㈡帴鍙ｏ紝璋冪敤 retriever.invoke(query) 灏变細杩斿洖鐩稿叧鏂囨。鍒楄〃
    prompt = ChatPromptTemplate.from_template(
        "浣犳槸鎶€鏈垎鏋愬姪鎵嬨€傛牴鎹弬鑰冭祫鏂欏洖绛旈棶棰樸€俓n"
        "濡傛灉鍙傝€冭祫鏂欏寘鍚〃鏍兼暟鎹紝璇峰熀浜庤〃鏍艰繘琛屽姣斿垎鏋愩€俓n"
        "濡傛灉淇℃伅涓嶈冻锛屾槑纭鏄庛€俓n\n"
        "鍙傝€冭祫鏂?\n{context}\n\n"
        "闂: {question}\n\n"
        "鍥炵瓟锛?)
    llm = ChatOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL, model="glm-4-flash", temperature=0.7)
    def format_docs(docs): #docs鏄摢閲屼紶杩囨潵鐨勶紵 涓嬮潰鐨?chain 瀹氫箟閲?retriever | format_docs 灏辨槸璇村厛璋冪敤 retriever.invoke(question) 寰楀埌 docs 鍒楄〃锛屽啀浼犵粰 format_docs 杩涜鏍煎紡鍖?        parts = []
        for i, d in enumerate(docs):  
            tag = "[琛ㄦ牸]" if d.metadata.get("type") == "Table" else "[鏂囨湰]"
            parts.append(f"鐗囨{i+1} {tag}:\n{d.page_content}")
        return "\n\n".join(parts) #灏嗘绱㈠埌鐨勬枃妗ｅ垪琛ㄦ牸寮忓寲鎴愪竴涓瓧绗︿覆锛岃〃鏍煎墠浼氭湁[琛ㄦ牸]鏍囩锛屾枃鏈墠浼氭湁[鏂囨湰]鏍囩锛屼究浜庢彁绀鸿瘝鍖哄垎
    chain = ({"context": retriever | format_docs, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser())
    return chain, retriever


# ========== 5. 娴嬭瘯 ==========
def run_test(chain, retriever):
    questions = [
        "鏈夊摢浜涘悜閲忔暟鎹簱锛熷畠浠湁浠€涔堝尯鍒紵",
        "RAG 绯荤粺鍖呭惈鍝簺鐜妭锛?,
        "Milvus 鐨勬渶澶ф暟鎹妯℃槸澶氬皯锛?,
    ]
    for i, q in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"闂 {i+1}: {q}")
        print(f"{'=' * 60}")
        docs = retriever.invoke(q)
        print(f"妫€绱㈠埌 {len(docs)} 涓墖娈?")
        for j, d in enumerate(docs):
            tag = "[琛ㄦ牸]" if d.metadata.get("type") == "Table" else "[鏂囨湰]"
            print(f"  [{j+1}] {tag} {d.page_content[:80]}...")
        print(f"\n鍥炵瓟:\n  {chain.invoke(q)}")


# ========== 涓诲嚱鏁?==========
if __name__ == "__main__":
    try:
        elements = partition_pdf(str(PDF_PATH)) # 瑙ｆ瀽 PDF锛屽緱鍒颁竴涓?Element 瀵硅薄鍒楄〃锛屾瘡涓璞″寘鍚簡鏂囨湰鍐呭鍜屽厓鏁版嵁锛堝椤电爜銆佽〃鏍艰鍒楁暟绛夛級
        documents = elements_to_documents(elements) # 灏?Element 瀵硅薄鍒楄〃杞负 LangChain Document 鍒楄〃锛岃〃鏍兼暣浣撲繚鐣欏苟鏍囪 type=Table
        embeddings = FastEmbedEmbeddings(EMBEDDING_MODEL)
        vs = MilvusVectorStore.from_documents(documents, embeddings, collection_name=COLLECTION_NAME, uri=MILVUS_URI) 
        # 灏?Document 鍒楄〃瀛樺叆 Milvus 鍚戦噺搴擄紝鍒涘缓闆嗗悎鍜岀储寮?杩斿洖鐨剉s鏄竴涓?MilvusVectorStore 瀹炰緥锛屽皝瑁呬簡 Milvus 鐨勬绱㈡帴鍙?        chain, retriever = build_rag_chain(vs)
        run_test(chain, retriever)
        print(f"\n{'=' * 60}")
        print("[OK] 澶嶆潅鏂囨。瑙ｆ瀽 + RAG 闆嗘垚婕旂ず瀹屾垚锛?)
        print("鏍稿績鏀惰幏锛?)
        print("  1. 鎸夊厓绱犵被鍨嬭В鏋愶紝琛ㄦ牸鏁翠綋淇濈暀涓嶅垏纰?)
        print("  2. 琛ㄦ牸杞?Markdown 淇濈暀缁撴瀯锛孡LM 鑳界悊瑙ｅ苟鍋氬姣斿垎鏋?)
        print("  3. 鍏冩暟鎹爣璁?type=Table 渚夸簬妫€绱㈡椂鍖哄垎")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

