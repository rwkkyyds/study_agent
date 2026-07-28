"""
Demo1: Advanced RAG 系统（Week 2 周 Demo）
集成：复杂文档解析 + 混合检索(BM25+向量) + RRF融合 + Rerank重排 + Milvus
对比：Naive RAG vs Advanced RAG 效果差异
依赖：pip install reportlab pdfplumber pymilvus fastembed langchain-openai rank_bm25 sentence-transformers
前提：docker compose up -d 启动 Milvus 服务
运行：docker build -t rag-demo . && docker run --rm --add-host host.docker.internal:host-gateway rag-demo
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os
from pathlib import Path
from dataclasses import dataclass, field 
# dataclass 用于定义简单的数据结构，field 用于指定字段的默认值或元数据

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
# BM25 是一种经典的关键词检索算法，rank_bm25 是 Python 的 BM25 实现库，
# 提供了 BM25Okapi 类来进行检索
from flashrank import Ranker, RerankRequest


# ========== 配置 ==========
DEMO_DIR = Path(__file__).parent / "demo_files"
DEMO_DIR.mkdir(exist_ok=True)
PDF_PATH = DEMO_DIR / "sample_rag_doc.pdf"
MILVUS_URI = os.environ.get("MILVUS_URI", "http://localhost:19530")
COLLECTION_NAME = "demo_advanced_rag"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
VECTOR_DIM = 512
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
RERANK_MODEL = os.environ.get("RERANK_MODEL", "ms-marco-MultiBERT-L-12")
# FlashRank 重排模型（多语言，支持中英文），基于 onnxruntime，无需 PyTorch
 

# ========== 元素类型 ==========
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


# ========== 1. PDF 解析（Section 5 知识点） ==========
def _find_cjk_font():
    """查找可用的中文字体，兼容 Linux 容器和 Windows"""
    candidates = [
        # Linux 常见路径
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        # Windows 路径
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def create_sample_pdf():
    """创建示例 PDF"""
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
        print("[WARN] 未找到中文字体，PDF 中的中文可能显示为方块")

    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=A4)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CNTitle", parent=styles["Title"], fontName=font_name, fontSize=16)
    heading_style = ParagraphStyle("CNHeading", parent=styles["Heading2"], fontName=font_name, fontSize=12)
    body_style = ParagraphStyle("CNBody", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=16)
    list_style = ParagraphStyle("CNList", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=16, leftIndent=20)

    elements = []
    elements.append(Paragraph("RAG 系统技术选型与优化报告", title_style))
    elements.append(Spacer(1, 10))

    # 正文1：RAG 概述
    elements.append(Paragraph(
        "RAG（检索增强生成）通过检索外部知识库来增强大模型的回答能力，减少幻觉。"
        "一个完整的 RAG 系统包含文档解析、文本分块、向量化、向量存储、检索、重排、生成等环节。"
        "Naive RAG 的问题在于检索精度不足，Advanced RAG 通过混合检索和重排来解决。", body_style))
    elements.append(Spacer(1, 10))

    # 表格：向量数据库对比
    elements.append(Paragraph("一、向量数据库对比", heading_style))
    elements.append(Spacer(1, 5))
    headers = ["数据库", "定位", "最大规模", "分布式", "适用场景"]
    rows = [
        ["FAISS", "向量检索库", "千万级", "否", "本地实验"],
        ["Chroma", "轻量向量库", "十万级", "否", "原型开发"],
        ["Milvus", "生产级向量库", "十亿级", "是", "生产部署"],
        ["Pinecone", "云向量服务", "十亿级", "是", "SaaS场景"],
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

    # 正文2：检索优化
    elements.append(Paragraph("二、检索优化策略", heading_style))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(
        "混合检索结合了 BM25 关键词检索和向量语义检索的优势。"
        "BM25 擅长精确关键词匹配，向量检索擅长语义相似度匹配。"
        "通过 RRF（Reciprocal Rank Fusion）融合两路检索结果，取长补短。", body_style))
    elements.append(Spacer(1, 10))

    # 正文3：重排
    elements.append(Paragraph("三、Rerank 重排", heading_style))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(
        "CrossEncoder 将 Query 和 Document 拼接后一起编码，能捕捉更细粒度的语义关系。"
        "它的精度高于 Bi-Encoder（向量检索用的），但速度慢，适合对 Top-K 结果做精排。"
        "典型的两阶段检索架构：第一阶段 BM25+向量粗召回，第二阶段 CrossEncoder 精排。", body_style))
    elements.append(Spacer(1, 10))

    # 列表：优化要点
    elements.append(Paragraph("四、Advanced RAG 优化要点", heading_style))
    elements.append(Spacer(1, 5))
    points = [
        "1. 文档解析：按元素类型解析，表格整体保留不切碎",
        "2. 混合检索：BM25（关键词）+ 向量（语义）双路召回",
        "3. RRF 融合：融合两路检索结果，综合排名",
        "4. Rerank 重排：CrossEncoder 精排，提升 Top-K 精度",
        "5. 向量库：Milvus 生产级部署，支持十亿级数据",
    ]
    for point in points:
        elements.append(Paragraph(point, list_style))
        elements.append(Spacer(1, 4))

    doc.build(elements)
    print(f"[OK] 已创建示例 PDF: {PDF_PATH}")


def partition_pdf(filename: str) -> list[Element]:
    """按元素类型解析 PDF（Section 5 知识点）"""
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
                    if line.endswith("：") or line.endswith(":") or line.startswith(("一、", "二、", "三、", "四、")):
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
        print(f"[OK] Milvus 向量库就绪: {collection_name}, {len(texts)} 条")
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


# ========== 3. BM25 检索器（Section 2 知识点） ==========
class BM25Retriever:
    """
    BM25 稀疏检索器
    优势：精确关键词匹配，不依赖 Embedding 模型
    """
    def __init__(self, documents: list[Document]):
        self.documents = documents
        # 中文按字符分词（简单处理，生产环境用 jieba）
        tokenized = [list(doc.page_content) for doc in documents]
        self.bm25 = BM25Okapi(tokenized)

    def invoke(self, query: str, k: int = 3) -> list[Document]:
        tokenized_query = list(query)
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:k]
        return [self.documents[i] for i in top_indices]


# ========== 4. RRF 融合（Section 2 知识点） ==========
def rrf_fusion(results_list: list[list[Document]], k: int = 60) -> list[Document]:
    """
    RRF（Reciprocal Rank Fusion）融合多路检索结果
    公式：score = sum(1 / (k + rank_i))
    优势：不需要归一化分数，直接用排名融合
    """
    doc_scores = {}
    for results in results_list:
        for rank, doc in enumerate(results):
            doc_key = doc.page_content[:100]  # 用内容前100字符做去重key
            if doc_key not in doc_scores:
                doc_scores[doc_key] = {"doc": doc, "score": 0}
            doc_scores[doc_key]["score"] += 1 / (k + rank + 1)

    sorted_docs = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)
    return [item["doc"] for item in sorted_docs]


# ========== 5. Rerank 重排（Section 2 知识点） ==========
class Reranker:
    """
    Rerank 精排器（基于 FlashRank，纯 onnxruntime，无需 PyTorch）
    将 Query + Document 拼接后一起编码，捕捉细粒度语义关系
    精度高于 Bi-Encoder，但速度慢，适合对 Top-K 做精排
    """
    def __init__(self, model_name: str = RERANK_MODEL):
        print(f"[INFO] 加载 Rerank 模型: {model_name} ...")
        self.ranker = Ranker(model_name=model_name) 
        print(f"[OK] Rerank 模型已加载")

    def rerank(self, query: str, documents: list[Document], top_k: int = 3) -> list[Document]:
        if not documents:
            return []
        # FlashRank 要求 passages 格式: [{"id": 0, "text": "..."}, ...]
        passages = [{"id": i, "text": doc.page_content} for i, doc in enumerate(documents)]
        req = RerankRequest(query=query, passages=passages) # 构造 Rerank 请求对象，包含查询和候选文档
        results = self.ranker.rerank(req) # 调用 Rerank 模型进行重排，返回按相关性排序的结果列表，每个结果包含文档 ID 和分数
        # results 按分数降序排列，取 top_k
        reranked = []
        for r in results[:top_k]:
            reranked.append(documents[r["id"]])
        return reranked


# ========== 6. Advanced RAG 系统 ==========
def build_advanced_rag(vectorstore, documents, reranker, embeddings):
    """
    构建 Advanced RAG 链路：
    用户问题 → 混合检索(BM25+向量) → RRF融合 → Rerank重排 → LLM回答
    """
    bm25_retriever = BM25Retriever(documents) #基于原始文档构建 BM25 检索器，直接使用文本内容进行关键词检索
    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) # 基于向量库构建向量检索器，使用文本的向量表示进行语义检索

    prompt = ChatPromptTemplate.from_template(
        "你是技术分析助手。根据参考资料回答问题。\n"
        "如果参考资料包含表格数据，请基于表格进行对比分析。\n"
        "如果信息不足，明确说明。\n\n"
        "参考资料:\n{context}\n\n"
        "问题: {question}\n\n"
        "回答：")
    llm = ChatOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL, model="glm-4-flash", temperature=0.7)

    def format_docs(docs):
        parts = []
        for i, d in enumerate(docs):
            tag = "[表格]" if d.metadata.get("is_table") else "[文本]"
            parts.append(f"片段{i+1} {tag}:\n{d.page_content}")
        return "\n\n".join(parts)

    def advanced_retrieve(query: str) -> list[Document]:
        """混合检索 + RRF融合 + Rerank重排"""
        # 第一阶段：双路粗召回
        bm25_results = bm25_retriever.invoke(query, k=5)
        vector_results = vector_retriever.invoke(query)
        # RRF 融合
        fused = rrf_fusion([bm25_results, vector_results])
        # 第二阶段：CrossEncoder 精排
        reranked = reranker.rerank(query, fused, top_k=3) 
        return reranked  

    chain = ({"context": RunnablePassthrough() | advanced_retrieve | format_docs,
              "question": RunnablePassthrough()}
             | prompt | llm | StrOutputParser())
    return chain


# ========== 7. Naive RAG（对比用） ==========
def build_naive_rag(vectorstore):
    """Naive RAG：只用向量检索，无混合、无重排"""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    prompt = ChatPromptTemplate.from_template(
        "根据参考资料回答问题。\n\n参考资料:\n{context}\n\n问题: {question}\n\n回答：")
    llm = ChatOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL, model="glm-4-flash", temperature=0.7)
    def format_docs(docs):
        return "\n\n".join(d.page_content for d in docs)
    chain = ({"context": retriever | format_docs, "question": RunnablePassthrough()}
             | prompt | llm | StrOutputParser())
    return chain


# ========== 8. 对比测试 ==========
def compare_rag(naive_chain, advanced_chain, questions):
    """对比 Naive RAG 和 Advanced RAG 的回答效果"""
    for i, q in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"问题 {i+1}: {q}")
        print(f"{'=' * 60}")

        naive_answer = naive_chain.invoke(q)
        advanced_answer = advanced_chain.invoke(q)

        print(f"\n  [Naive RAG]\n    {naive_answer[:200]}...")
        print(f"\n  [Advanced RAG]\n    {advanced_answer[:200]}...")


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        print(f"[INFO] Milvus URI: {MILVUS_URI}")
        print(f"[INFO] 运行环境: {'Docker 容器' if os.path.exists('/.dockerenv') else '本机'}")

        # Step 1: 创建并解析 PDF
        create_sample_pdf()
        elements = partition_pdf(str(PDF_PATH)) # 解析 PDF，得到按元素类型划分的内容块
        documents = []
        for elem in elements:
            content = elem.text
            metadata = {**elem.metadata, "type": type(elem).__name__} 
            #elem.metadata 包含 page 和 is_table 信息，type(elem).__name__ 包含元素类型（Title、NarrativeText、Table、ListItem）
            if isinstance(elem, Table):
                content = f"[表格数据]\n{content}\n[表格结束]"
            documents.append(Document(page_content=content, metadata=metadata))
        print(f"[OK] 解析完成: {len(documents)} 个文档")

        # Step 2: 存入 Milvus
        embeddings = FastEmbedEmbeddings(EMBEDDING_MODEL)
        vectorstore = MilvusVectorStore.from_documents(
            documents, embeddings, collection_name=COLLECTION_NAME, uri=MILVUS_URI)

        # Step 3: 加载 Rerank 模型
        reranker = Reranker()

        # Step 4: 构建两条 RAG 链
        naive_chain = build_naive_rag(vectorstore)
        advanced_chain = build_advanced_rag(vectorstore, documents, reranker, embeddings)

        # Step 5: 对比测试
        questions = [
            "有哪些向量数据库？它们有什么区别？",
            "RAG 系统如何优化检索精度？",
            "Milvus 适合什么场景？",
        ]
        compare_rag(naive_chain, advanced_chain, questions)

        print(f"\n{'=' * 60}")
        print("[OK] Week 2 周 Demo 完成！")
        print("Advanced RAG = 混合" \
        "检索 + RRF融合 + Rerank重排 + Milvus")
        print("核心提升：检索精度和回答质量显著优于 Naive RAG")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
