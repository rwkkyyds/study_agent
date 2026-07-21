"""
Demo1: Advanced RAG 绯荤粺锛圵eek 2 鍛?Demo锛?闆嗘垚锛氬鏉傛枃妗ｈВ鏋?+ 娣峰悎妫€绱?BM25+鍚戦噺) + RRF铻嶅悎 + Rerank閲嶆帓 + Milvus
瀵规瘮锛歂aive RAG vs Advanced RAG 鏁堟灉宸紓
渚濊禆锛歱ip install reportlab pdfplumber pymilvus fastembed langchain-openai rank_bm25 sentence-transformers
鍓嶆彁锛歞ocker compose up -d 鍚姩 Milvus 鏈嶅姟
杩愯锛歞ocker build -t rag-demo . && docker run --rm --add-host host.docker.internal:host-gateway rag-demo
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os
from pathlib import Path
from dataclasses import dataclass, field 
# dataclass 鐢ㄤ簬瀹氫箟绠€鍗曠殑鏁版嵁缁撴瀯锛宖ield 鐢ㄤ簬鎸囧畾瀛楁鐨勯粯璁ゅ€兼垨鍏冩暟鎹?
import pdfplumber
import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from fastembed import TextEmbedding
from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema
from rank_bm25 import BM25Okapi 
# BM25 鏄竴绉嶇粡鍏哥殑鍏抽敭璇嶆绱㈢畻娉曪紝rank_bm25 鏄?Python 鐨?BM25 瀹炵幇搴擄紝
# 鎻愪緵浜?BM25Okapi 绫绘潵杩涜妫€绱?from flashrank import Ranker, RerankRequest


# ========== 閰嶇疆 ==========
DEMO_DIR = Path(__file__).parent / "demo_files"
DEMO_DIR.mkdir(exist_ok=True)
PDF_PATH = DEMO_DIR / "sample_rag_doc.pdf"
MILVUS_URI = os.environ.get("MILVUS_URI", "http://localhost:19530")
COLLECTION_NAME = "demo_advanced_rag"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
VECTOR_DIM = 512
ZHIPU_API_KEY = __import__("os").environ.get("ZHIPU_API_KEY")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
RERANK_MODEL = os.environ.get("RERANK_MODEL", "ms-marco-MultiBERT-L-12")
# FlashRank 閲嶆帓妯″瀷锛堝璇█锛屾敮鎸佷腑鑻辨枃锛夛紝鍩轰簬 onnxruntime锛屾棤闇€ PyTorch
 

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


# ========== 1. PDF 瑙ｆ瀽锛圫ection 5 鐭ヨ瘑鐐癸級 ==========
def _find_cjk_font():
    """鏌ユ壘鍙敤鐨勪腑鏂囧瓧浣擄紝鍏煎 Linux 瀹瑰櫒鍜?Windows"""
    candidates = [
        # Linux 甯歌璺緞
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        # Windows 璺緞
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def create_sample_pdf():
    """鍒涘缓绀轰緥 PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table as RLTable, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_path = _find_cjk_font()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont("CJK", font_path, subfontIndex=0))
            font_name = "CJK"
        except Exception:
            font_name = "Helvetica"
    else:
        font_name = "Helvetica"
        print("[WARN] 鏈壘鍒颁腑鏂囧瓧浣擄紝PDF 涓殑涓枃鍙兘鏄剧ず涓烘柟鍧?)

    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=A4)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CNTitle", parent=styles["Title"], fontName=font_name, fontSize=16)
    heading_style = ParagraphStyle("CNHeading", parent=styles["Heading2"], fontName=font_name, fontSize=12)
    body_style = ParagraphStyle("CNBody", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=16)
    list_style = ParagraphStyle("CNList", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=16, leftIndent=20)

    elements = []
    elements.append(Paragraph("RAG 绯荤粺鎶€鏈€夊瀷涓庝紭鍖栨姤鍛?, title_style))
    elements.append(Spacer(1, 10))

    # 姝ｆ枃1锛歊AG 姒傝堪
    elements.append(Paragraph(
        "RAG锛堟绱㈠寮虹敓鎴愶級閫氳繃妫€绱㈠閮ㄧ煡璇嗗簱鏉ュ寮哄ぇ妯″瀷鐨勫洖绛旇兘鍔涳紝鍑忓皯骞昏銆?
        "涓€涓畬鏁寸殑 RAG 绯荤粺鍖呭惈鏂囨。瑙ｆ瀽銆佹枃鏈垎鍧椼€佸悜閲忓寲銆佸悜閲忓瓨鍌ㄣ€佹绱€侀噸鎺掋€佺敓鎴愮瓑鐜妭銆?
        "Naive RAG 鐨勯棶棰樺湪浜庢绱㈢簿搴︿笉瓒筹紝Advanced RAG 閫氳繃娣峰悎妫€绱㈠拰閲嶆帓鏉ヨВ鍐炽€?, body_style))
    elements.append(Spacer(1, 10))

    # 琛ㄦ牸锛氬悜閲忔暟鎹簱瀵规瘮
    elements.append(Paragraph("涓€銆佸悜閲忔暟鎹簱瀵规瘮", heading_style))
    elements.append(Spacer(1, 5))
    headers = ["鏁版嵁搴?, "瀹氫綅", "鏈€澶ц妯?, "鍒嗗竷寮?, "閫傜敤鍦烘櫙"]
    rows = [
        ["FAISS", "鍚戦噺妫€绱㈠簱", "鍗冧竾绾?, "鍚?, "鏈湴瀹為獙"],
        ["Chroma", "杞婚噺鍚戦噺搴?, "鍗佷竾绾?, "鍚?, "鍘熷瀷寮€鍙?],
        ["Milvus", "鐢熶骇绾у悜閲忓簱", "鍗佷嚎绾?, "鏄?, "鐢熶骇閮ㄧ讲"],
        ["Pinecone", "浜戝悜閲忔湇鍔?, "鍗佷嚎绾?, "鏄?, "SaaS鍦烘櫙"],
    ]
    table_data = [headers] + rows
    table = RLTable(table_data, colWidths=[60, 70, 50, 40, 70])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 15))

    # 姝ｆ枃2锛氭绱紭鍖?    elements.append(Paragraph("浜屻€佹绱紭鍖栫瓥鐣?, heading_style))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(
        "娣峰悎妫€绱㈢粨鍚堜簡 BM25 鍏抽敭璇嶆绱㈠拰鍚戦噺璇箟妫€绱㈢殑浼樺娍銆?
        "BM25 鎿呴暱绮剧‘鍏抽敭璇嶅尮閰嶏紝鍚戦噺妫€绱㈡搮闀胯涔夌浉浼煎害鍖归厤銆?
        "閫氳繃 RRF锛圧eciprocal Rank Fusion锛夎瀺鍚堜袱璺绱㈢粨鏋滐紝鍙栭暱琛ョ煭銆?, body_style))
    elements.append(Spacer(1, 10))

    # 姝ｆ枃3锛氶噸鎺?    elements.append(Paragraph("涓夈€丷erank 閲嶆帓", heading_style))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(
        "CrossEncoder 灏?Query 鍜?Document 鎷兼帴鍚庝竴璧风紪鐮侊紝鑳芥崟鎹夋洿缁嗙矑搴︾殑璇箟鍏崇郴銆?
        "瀹冪殑绮惧害楂樹簬 Bi-Encoder锛堝悜閲忔绱㈢敤鐨勶級锛屼絾閫熷害鎱紝閫傚悎瀵?Top-K 缁撴灉鍋氱簿鎺掋€?
        "鍏稿瀷鐨勪袱闃舵妫€绱㈡灦鏋勶細绗竴闃舵 BM25+鍚戦噺绮楀彫鍥烇紝绗簩闃舵 CrossEncoder 绮炬帓銆?, body_style))
    elements.append(Spacer(1, 10))

    # 鍒楄〃锛氫紭鍖栬鐐?    elements.append(Paragraph("鍥涖€丄dvanced RAG 浼樺寲瑕佺偣", heading_style))
    elements.append(Spacer(1, 5))
    points = [
        "1. 鏂囨。瑙ｆ瀽锛氭寜鍏冪礌绫诲瀷瑙ｆ瀽锛岃〃鏍兼暣浣撲繚鐣欎笉鍒囩",
        "2. 娣峰悎妫€绱細BM25锛堝叧閿瘝锛? 鍚戦噺锛堣涔夛級鍙岃矾鍙洖",
        "3. RRF 铻嶅悎锛氳瀺鍚堜袱璺绱㈢粨鏋滐紝缁煎悎鎺掑悕",
        "4. Rerank 閲嶆帓锛欳rossEncoder 绮炬帓锛屾彁鍗?Top-K 绮惧害",
        "5. 鍚戦噺搴擄細Milvus 鐢熶骇绾ч儴缃诧紝鏀寔鍗佷嚎绾ф暟鎹?,
    ]
    for point in points:
        elements.append(Paragraph(point, list_style))
        elements.append(Spacer(1, 4))

    doc.build(elements)
    print(f"[OK] 宸插垱寤虹ず渚?PDF: {PDF_PATH}")


def partition_pdf(filename: str) -> list[Element]:
    """鎸夊厓绱犵被鍨嬭В鏋?PDF锛圫ection 5 鐭ヨ瘑鐐癸級"""
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
                    if line.endswith("锛?) or line.endswith(":") or line.startswith(("涓€銆?, "浜屻€?, "涓夈€?, "鍥涖€?)):
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
                    elements.append(Table(text=md, metadata={"page": page_num + 1, "is_table": True}))
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


# ========== 2. Embedding + VectorStore ==========
class FastEmbedEmbeddings(Embeddings):
    def __init__(self, model_name):
        super().__init__()
        self.model = TextEmbedding(model_name)
    def embed_documents(self, texts):
        return [list(v) for v in self.model.embed(texts)]
    def embed_query(self, text):
        return list(list(self.model.embed([text]))[0])

class MilvusVectorStore(VectorStore):
    def __init__(self, client, collection_name, embedding):
        self.client = client
        self.collection_name = collection_name
        self.embedding = embedding

    @classmethod
    def from_texts(cls, texts, embedding, metadatas=None, collection_name="default", **kwargs):
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
        texts = [d.page_content for d in documents]
        metadatas = [d.metadata for d in documents]
        return cls.from_texts(texts, embedding, metadatas, collection_name, **kwargs)

    def similarity_search(self, query, k=4, **kwargs):
        qv = self.embedding.embed_query(query)
        results = self.client.search(collection_name=self.collection_name, data=[qv], limit=k,
                                     output_fields=["text", "metadata"],
                                     search_params={"metric_type": "COSINE"})
        return [Document(page_content=hit["entity"]["text"],
                         metadata=hit["entity"].get("metadata", {})) for hit in results[0]]


# ========== 3. BM25 妫€绱㈠櫒锛圫ection 2 鐭ヨ瘑鐐癸級 ==========
class BM25Retriever:
    """
    BM25 绋€鐤忔绱㈠櫒
    浼樺娍锛氱簿纭叧閿瘝鍖归厤锛屼笉渚濊禆 Embedding 妯″瀷
    """
    def __init__(self, documents: list[Document]):
        self.documents = documents
        # 涓枃鎸夊瓧绗﹀垎璇嶏紙绠€鍗曞鐞嗭紝鐢熶骇鐜鐢?jieba锛?        tokenized = [list(doc.page_content) for doc in documents]
        self.bm25 = BM25Okapi(tokenized)

    def invoke(self, query: str, k: int = 3) -> list[Document]:
        tokenized_query = list(query)
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:k]
        return [self.documents[i] for i in top_indices]


# ========== 4. RRF 铻嶅悎锛圫ection 2 鐭ヨ瘑鐐癸級 ==========
def rrf_fusion(results_list: list[list[Document]], k: int = 60) -> list[Document]:
    """
    RRF锛圧eciprocal Rank Fusion锛夎瀺鍚堝璺绱㈢粨鏋?    鍏紡锛歴core = sum(1 / (k + rank_i))
    浼樺娍锛氫笉闇€瑕佸綊涓€鍖栧垎鏁帮紝鐩存帴鐢ㄦ帓鍚嶈瀺鍚?    """
    doc_scores = {}
    for results in results_list:
        for rank, doc in enumerate(results):
            doc_key = doc.page_content[:100]  # 鐢ㄥ唴瀹瑰墠100瀛楃鍋氬幓閲峩ey
            if doc_key not in doc_scores:
                doc_scores[doc_key] = {"doc": doc, "score": 0}
            doc_scores[doc_key]["score"] += 1 / (k + rank + 1)

    sorted_docs = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)
    return [item["doc"] for item in sorted_docs]


# ========== 5. Rerank 閲嶆帓锛圫ection 2 鐭ヨ瘑鐐癸級 ==========
class Reranker:
    """
    Rerank 绮炬帓鍣紙鍩轰簬 FlashRank锛岀函 onnxruntime锛屾棤闇€ PyTorch锛?    灏?Query + Document 鎷兼帴鍚庝竴璧风紪鐮侊紝鎹曟崏缁嗙矑搴﹁涔夊叧绯?    绮惧害楂樹簬 Bi-Encoder锛屼絾閫熷害鎱紝閫傚悎瀵?Top-K 鍋氱簿鎺?    """
    def __init__(self, model_name: str = RERANK_MODEL):
        print(f"[INFO] 鍔犺浇 Rerank 妯″瀷: {model_name} ...")
        self.ranker = Ranker(model_name=model_name) 
        print(f"[OK] Rerank 妯″瀷宸插姞杞?)

    def rerank(self, query: str, documents: list[Document], top_k: int = 3) -> list[Document]:
        if not documents:
            return []
        # FlashRank 瑕佹眰 passages 鏍煎紡: [{"id": 0, "text": "..."}, ...]
        passages = [{"id": i, "text": doc.page_content} for i, doc in enumerate(documents)]
        req = RerankRequest(query=query, passages=passages) # 鏋勯€?Rerank 璇锋眰瀵硅薄锛屽寘鍚煡璇㈠拰鍊欓€夋枃妗?        results = self.ranker.rerank(req) # 璋冪敤 Rerank 妯″瀷杩涜閲嶆帓锛岃繑鍥炴寜鐩稿叧鎬ф帓搴忕殑缁撴灉鍒楄〃锛屾瘡涓粨鏋滃寘鍚枃妗?ID 鍜屽垎鏁?        # results 鎸夊垎鏁伴檷搴忔帓鍒楋紝鍙?top_k
        reranked = []
        for r in results[:top_k]:
            reranked.append(documents[r["id"]])
        return reranked


# ========== 6. Advanced RAG 绯荤粺 ==========
def build_advanced_rag(vectorstore, documents, reranker, embeddings):
    """
    鏋勫缓 Advanced RAG 閾捐矾锛?    鐢ㄦ埛闂 鈫?娣峰悎妫€绱?BM25+鍚戦噺) 鈫?RRF铻嶅悎 鈫?Rerank閲嶆帓 鈫?LLM鍥炵瓟
    """
    bm25_retriever = BM25Retriever(documents) #鍩轰簬鍘熷鏂囨。鏋勫缓 BM25 妫€绱㈠櫒锛岀洿鎺ヤ娇鐢ㄦ枃鏈唴瀹硅繘琛屽叧閿瘝妫€绱?    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) # 鍩轰簬鍚戦噺搴撴瀯寤哄悜閲忔绱㈠櫒锛屼娇鐢ㄦ枃鏈殑鍚戦噺琛ㄧず杩涜璇箟妫€绱?
    prompt = ChatPromptTemplate.from_template(
        "浣犳槸鎶€鏈垎鏋愬姪鎵嬨€傛牴鎹弬鑰冭祫鏂欏洖绛旈棶棰樸€俓n"
        "濡傛灉鍙傝€冭祫鏂欏寘鍚〃鏍兼暟鎹紝璇峰熀浜庤〃鏍艰繘琛屽姣斿垎鏋愩€俓n"
        "濡傛灉淇℃伅涓嶈冻锛屾槑纭鏄庛€俓n\n"
        "鍙傝€冭祫鏂?\n{context}\n\n"
        "闂: {question}\n\n"
        "鍥炵瓟锛?)
    llm = ChatOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL, model="glm-4-flash", temperature=0.7)

    def format_docs(docs):
        parts = []
        for i, d in enumerate(docs):
            tag = "[琛ㄦ牸]" if d.metadata.get("is_table") else "[鏂囨湰]"
            parts.append(f"鐗囨{i+1} {tag}:\n{d.page_content}")
        return "\n\n".join(parts)

    def advanced_retrieve(query: str) -> list[Document]:
        """娣峰悎妫€绱?+ RRF铻嶅悎 + Rerank閲嶆帓"""
        # 绗竴闃舵锛氬弻璺矖鍙洖
        bm25_results = bm25_retriever.invoke(query, k=5)
        vector_results = vector_retriever.invoke(query)
        # RRF 铻嶅悎
        fused = rrf_fusion([bm25_results, vector_results])
        # 绗簩闃舵锛欳rossEncoder 绮炬帓
        reranked = reranker.rerank(query, fused, top_k=3) 
        return reranked  

    chain = ({"context": RunnablePassthrough() | advanced_retrieve | format_docs,
              "question": RunnablePassthrough()}
             | prompt | llm | StrOutputParser())
    return chain


# ========== 7. Naive RAG锛堝姣旂敤锛?==========
def build_naive_rag(vectorstore):
    """Naive RAG锛氬彧鐢ㄥ悜閲忔绱紝鏃犳贩鍚堛€佹棤閲嶆帓"""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    prompt = ChatPromptTemplate.from_template(
        "鏍规嵁鍙傝€冭祫鏂欏洖绛旈棶棰樸€俓n\n鍙傝€冭祫鏂?\n{context}\n\n闂: {question}\n\n鍥炵瓟锛?)
    llm = ChatOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL, model="glm-4-flash", temperature=0.7)
    def format_docs(docs):
        return "\n\n".join(d.page_content for d in docs)
    chain = ({"context": retriever | format_docs, "question": RunnablePassthrough()}
             | prompt | llm | StrOutputParser())
    return chain


# ========== 8. 瀵规瘮娴嬭瘯 ==========
def compare_rag(naive_chain, advanced_chain, questions):
    """瀵规瘮 Naive RAG 鍜?Advanced RAG 鐨勫洖绛旀晥鏋?""
    for i, q in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"闂 {i+1}: {q}")
        print(f"{'=' * 60}")

        naive_answer = naive_chain.invoke(q)
        advanced_answer = advanced_chain.invoke(q)

        print(f"\n  [Naive RAG]\n    {naive_answer[:200]}...")
        print(f"\n  [Advanced RAG]\n    {advanced_answer[:200]}...")


# ========== 涓诲嚱鏁?==========
if __name__ == "__main__":
    try:
        print(f"[INFO] Milvus URI: {MILVUS_URI}")
        print(f"[INFO] 杩愯鐜: {'Docker 瀹瑰櫒' if os.path.exists('/.dockerenv') else '鏈満'}")

        # Step 1: 鍒涘缓骞惰В鏋?PDF
        create_sample_pdf()
        elements = partition_pdf(str(PDF_PATH)) # 瑙ｆ瀽 PDF锛屽緱鍒版寜鍏冪礌绫诲瀷鍒掑垎鐨勫唴瀹瑰潡
        documents = []
        for elem in elements:
            content = elem.text
            metadata = {**elem.metadata, "type": type(elem).__name__} 
            #elem.metadata 鍖呭惈 page 鍜?is_table 淇℃伅锛宼ype(elem).__name__ 鍖呭惈鍏冪礌绫诲瀷锛圱itle銆丯arrativeText銆乀able銆丩istItem锛?            if isinstance(elem, Table):
                content = f"[琛ㄦ牸鏁版嵁]\n{content}\n[琛ㄦ牸缁撴潫]"
            documents.append(Document(page_content=content, metadata=metadata))
        print(f"[OK] 瑙ｆ瀽瀹屾垚: {len(documents)} 涓枃妗?)

        # Step 2: 瀛樺叆 Milvus
        embeddings = FastEmbedEmbeddings(EMBEDDING_MODEL)
        vectorstore = MilvusVectorStore.from_documents(
            documents, embeddings, collection_name=COLLECTION_NAME, uri=MILVUS_URI)

        # Step 3: 鍔犺浇 Rerank 妯″瀷
        reranker = Reranker()

        # Step 4: 鏋勫缓涓ゆ潯 RAG 閾?        naive_chain = build_naive_rag(vectorstore)
        advanced_chain = build_advanced_rag(vectorstore, documents, reranker, embeddings)

        # Step 5: 瀵规瘮娴嬭瘯
        questions = [
            "鏈夊摢浜涘悜閲忔暟鎹簱锛熷畠浠湁浠€涔堝尯鍒紵",
            "RAG 绯荤粺濡備綍浼樺寲妫€绱㈢簿搴︼紵",
            "Milvus 閫傚悎浠€涔堝満鏅紵",
        ]
        compare_rag(naive_chain, advanced_chain, questions)

        print(f"\n{'=' * 60}")
        print("[OK] Week 2 鍛?Demo 瀹屾垚锛?)
        print("Advanced RAG = 娣峰悎" \
        "妫€绱?+ RRF铻嶅悎 + Rerank閲嶆帓 + Milvus")
        print("鏍稿績鎻愬崌锛氭绱㈢簿搴﹀拰鍥炵瓟璐ㄩ噺鏄捐憲浼樹簬 Naive RAG")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

