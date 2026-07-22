"""
Demo2: 复杂文档解析 + RAG 集成
功能：PDF解析(按元素类型) → 表格/文本分离 → 分块 → Milvus → RAG问答
核心：表格整体保留不切碎，转Markdown供LLM理解
依赖：pip install reportlab pdfplumber pymilvus fastembed langchain-openai
前提：docker compose up -d 启动 Milvus 服务
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


# ========== 配置 ==========
DEMO_DIR = Path(__file__).parent / "demo_files"
PDF_PATH = DEMO_DIR / "sample_rag_doc.pdf"
MILVUS_URI = "http://localhost:19530"
COLLECTION_NAME = "demo_rag_parsed_doc"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
VECTOR_DIM = 512
ZHIPU_API_KEY = "70041ddde9824461bfb02fac3f469fc3.pDZCoxOgkovIx1vT"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"


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


# ========== 1. PDF 按元素类型解析 ==========
def partition_pdf(filename: str) -> list[Element]:
    """按元素类型解析 PDF（对标 Unstructured partition_pdf）"""
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
                    if line.endswith("：") or line.endswith(":") or line.startswith(("一、", "二、", "三、")):
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


# ========== 2. 元素转 RAG 文档 ==========
def elements_to_documents(elements: list[Element]) -> list[Document]:
    """将解析元素转为 LangChain Document，表格整体保留"""
    docs = []
    for elem in elements:
        content = elem.text
        metadata = {**elem.metadata, "type": type(elem).__name__}
        if isinstance(elem, Table):
            content = f"[表格数据]\n{content}\n[表格结束]"
        docs.append(Document(page_content=content, metadata=metadata))
    print(f"[OK] 已准备 {len(docs)} 个 RAG 文档")
    return docs


# ========== 3. Embedding + VectorStore ==========
class FastEmbedEmbeddings(Embeddings):   #封装 FastEmbed 的文本嵌入接口，适配 LangChain Embeddings 接口
    def __init__(self, model_name):
        super().__init__()
        self.model = TextEmbedding(model_name)
    def embed_documents(self, texts):
        return [list(v) for v in self.model.embed(texts)] #返回一个二维列表，每个子列表是对应文本的向量表示
    def embed_query(self, text):
        return list(list(self.model.embed([text]))[0]) #返回一个一维列表，是查询文本的向量表示

class MilvusVectorStore(VectorStore):  # 封装 Milvus 向量库的接口，适配 LangChain VectorStore 接口 有as_retriever方法可以直接转为 LangChain Retriever接口
    def __init__(self, client, collection_name, embedding):
        self.client = client
        self.collection_name = collection_name
        self.embedding = embedding

    @classmethod
    def from_texts(cls, texts, embedding, metadatas=None, collection_name="default", **kwargs): 
        #根据文本列表创建 Milvus 向量库实例，先创建集合和索引，再批量插入数据
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
        print(f"[OK] Milvus 向量库就绪: {collection_name}, {len(documents)} 条")
        return cls(client=client, collection_name=collection_name, embedding=embedding) 
        #返回的是一个 MilvusVectorStore 实例，封装了 Milvus 的检索接口, 有as_retriever方法可以直接转为 LangChain Retriever接口

    def similarity_search(self, query, k=4, **kwargs):
        qv = self.embedding.embed_query(query)
        results = self.client.search(collection_name=self.collection_name, data=[qv], limit=k,
                                     output_fields=["text", "metadata"],
                                     search_params={"metric_type": "COSINE"})
        return [Document(page_content=hit["entity"]["text"],
                         metadata=hit["entity"].get("metadata", {})) for hit in results[0]]


# ========== 4. RAG 链路 ==========
def build_rag_chain(vectorstore):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) #返回格式 eg: [Document(page_content='[表格数据]\n| 向量数据库 | 适用场景 |\n| --- | --- |\n| Milvus | 大规模向量检索 |\n| FAISS | 本地小规模检索 |\n[表格结束]', metadata={'page': 2, 'type': 'Table'})]
    #返回一个 Retriever 实例，封装了 Milvus 的检索接口，调用 retriever.invoke(query) 就会返回相关文档列表
    prompt = ChatPromptTemplate.from_template(
        "你是技术分析助手。根据参考资料回答问题。\n"
        "如果参考资料包含表格数据，请基于表格进行对比分析。\n"
        "如果信息不足，明确说明。\n\n"
        "参考资料:\n{context}\n\n"
        "问题: {question}\n\n"
        "回答：")
    llm = ChatOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL, model="glm-4-flash", temperature=0.7)
    def format_docs(docs): #docs是哪里传过来的？ 下面的 chain 定义里 retriever | format_docs 就是说先调用 retriever.invoke(question) 得到 docs 列表，再传给 format_docs 进行格式化
        parts = []
        for i, d in enumerate(docs):  
            tag = "[表格]" if d.metadata.get("type") == "Table" else "[文本]"
            parts.append(f"片段{i+1} {tag}:\n{d.page_content}")
        return "\n\n".join(parts) #将检索到的文档列表格式化成一个字符串，表格前会有[表格]标签，文本前会有[文本]标签，便于提示词区分
    chain = ({"context": retriever | format_docs, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser())
    return chain, retriever


# ========== 5. 测试 ==========
def run_test(chain, retriever):
    questions = [
        "有哪些向量数据库？它们有什么区别？",
        "RAG 系统包含哪些环节？",
        "Milvus 的最大数据规模是多少？",
    ]
    for i, q in enumerate(questions):
        print(f"\n{'=' * 60}")
        print(f"问题 {i+1}: {q}")
        print(f"{'=' * 60}")
        docs = retriever.invoke(q)
        print(f"检索到 {len(docs)} 个片段:")
        for j, d in enumerate(docs):
            tag = "[表格]" if d.metadata.get("type") == "Table" else "[文本]"
            print(f"  [{j+1}] {tag} {d.page_content[:80]}...")
        print(f"\n回答:\n  {chain.invoke(q)}")


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        elements = partition_pdf(str(PDF_PATH)) # 解析 PDF，得到一个 Element 对象列表，每个对象包含了文本内容和元数据（如页码、表格行列数等）
        documents = elements_to_documents(elements) # 将 Element 对象列表转为 LangChain Document 列表，表格整体保留并标记 type=Table
        embeddings = FastEmbedEmbeddings(EMBEDDING_MODEL)
        vs = MilvusVectorStore.from_documents(documents, embeddings, collection_name=COLLECTION_NAME, uri=MILVUS_URI) 
        # 将 Document 列表存入 Milvus 向量库，创建集合和索引 返回的vs是一个 MilvusVectorStore 实例，封装了 Milvus 的检索接口
        chain, retriever = build_rag_chain(vs)
        run_test(chain, retriever)
        print(f"\n{'=' * 60}")
        print("[OK] 复杂文档解析 + RAG 集成演示完成！")
        print("核心收获：")
        print("  1. 按元素类型解析，表格整体保留不切碎")
        print("  2. 表格转 Markdown 保留结构，LLM 能理解并做对比分析")
        print("  3. 元数据标记 type=Table 便于检索时区分")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
