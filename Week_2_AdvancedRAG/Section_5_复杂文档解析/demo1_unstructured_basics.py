"""
Demo1: 复杂文档解析基础（对标 Unstructured 思想）
功能：创建示例PDF → 按元素类型解析 → 表格/文本/列表分离
核心思想：Unstructured 的 partition_pdf 就是按元素类型分别解析，而不是按字符数切分
依赖：pip install reportlab pdfplumber pypdf
注意：Unstructured 在 Windows 上依赖冲突严重（PyTorch/onnxruntime DLL），
     本 demo 用 pdfplumber+pypdf 实现相同的解析逻辑，理解原理即可。
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ========== 配置 ==========  
DEMO_DIR = Path(__file__).parent / "demo_files" 
DEMO_DIR.mkdir(exist_ok=True)
PDF_PATH = DEMO_DIR / "sample_rag_doc.pdf"


# ========== 0. 元素类型定义（对标 Unstructured 的 Element 体系） ==========
@dataclass
class Element:
    """基础元素类（对标 unstructured.documents.elements.Element）"""
    text: str
    metadata: dict = field(default_factory=dict)

@dataclass
class Title(Element):
    """标题元素"""
    pass

@dataclass
class NarrativeText(Element):
    """正文段落元素"""
    pass

@dataclass
class Table(Element):
    """表格元素（关键：整体保留，不切碎）"""
    html: str = ""  # 表格的 HTML 格式

@dataclass
class ListItem(Element):
    """列表项元素"""
    pass


# ========== 1. 创建示例 PDF ==========
def create_sample_pdf():
    """创建包含标题、正文、表格、列表的示例 PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table as RLTable, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_path = "C:/Windows/Fonts/msyh.ttc"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("msyh", font_path, subfontIndex=0))
        font_name = "msyh"
    else:
        font_name = "Helvetica"

    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=A4)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CNTitle", parent=styles["Title"], fontName=font_name, fontSize=16)
    heading_style = ParagraphStyle("CNHeading", parent=styles["Heading2"], fontName=font_name, fontSize=12)
    body_style = ParagraphStyle("CNBody", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=16)
    list_style = ParagraphStyle("CNList", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=16, leftIndent=20)

    elements = []
    elements.append(Paragraph("RAG 系统技术选型报告", title_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "RAG（检索增强生成）是当前最主流的大模型应用架构。"
        "它通过检索外部知识库来增强 LLM 的回答能力，减少幻觉。"
        "一个完整的 RAG 系统包含：文档解析、文本分块、向量化、"
        "向量存储、检索、重排、生成等环节。", body_style))
    elements.append(Spacer(1, 10))
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
    elements.append(Paragraph("二、RAG 优化要点", heading_style))
    elements.append(Spacer(1, 5))

    points = [
        "1. 文档解析：使用 Unstructured 处理复杂 PDF，保留表格和图片信息",
        "2. 分块策略：语义分块优于固定长度分块，保持上下文完整性",
        "3. 检索优化：混合检索（BM25 + 向量）+ Rerank 重排提升精度",
        "4. 评估体系：使用 RAGAs/DeepEval 量化评估，持续迭代优化",
    ]
    for point in points:
        elements.append(Paragraph(point, list_style))
        elements.append(Spacer(1, 4))

    doc.build(elements)
    print(f"[OK] 已创建示例 PDF: {PDF_PATH}")
    print(f"     包含：标题、正文、表格（{len(rows)}行）、列表（{len(points)}项）")


# ========== 2. 按元素类型解析（对标 Unstructured partition_pdf） ==========
def partition_pdf(filename: str) -> list[Element]:
    """
    按元素类型解析 PDF（对标 Unstructured 的 partition_pdf）
    核心思想：不是按字符数切分，而是识别文档结构，按元素类型分别处理
    """
    import pdfplumber
    elements = []
    with pdfplumber.open(filename) as pdf:
        for page_num, page in enumerate(pdf.pages): #pdf.pages 是一个列表，包含了 PDF 中的每一页 每一页是一个 Page 对象，提供了 extract_text() 和 extract_tables() 方法
            # 提取文本 
            text = page.extract_text() 
            #.extract_text() 方法会返回一个字符串，包含了该页的所有文本内容，文本内容会按照在 PDF 中的顺序进行排列，行与行之间会用换行符 \n 分隔
            if text:
                lines = text.split("\n") 
                current_block = [] #当前文本块（同一类型的连续行）
                current_type = "text"

                for line in lines:  # 遍历每一行文本，识别其类型（标题/列表/正文），并根据类型变化来划分元素块
                    line = line.strip()
                    if not line:
                        continue

                    # 识别元素类型
                    if _is_heading(line):
                        new_type = "heading"
                    elif _is_list_item(line):
                        new_type = "list"
                    else:
                        new_type = "text"

                    # 类型变化时保存当前块
                    if new_type != current_type and current_block: #如果当前行的类型与之前的类型不同，并且当前块不为空，则将当前块作为一个元素保存下来
                        elements.append(_create_element(current_type, "\n".join(current_block), page_num))
                        current_block = []

                    current_type = new_type
                    current_block.append(line)

                if current_block:
                    elements.append(_create_element(current_type, "\n".join(current_block), page_num))

            # 提取表格（整体保留，不切碎）
            tables = page.extract_tables() 
            for table_data in tables:               
 # extract_tables() 方法会返回一个列表，包含了该页的所有表格，每个表格是一个二维列表（list of lists），其中第一行通常是表头，后续行是表格内容
                if table_data and len(table_data) > 1:
                    md = _table_to_markdown(table_data)
                    html = _table_to_html(table_data)
                    elements.append(Table(
                        text=md,
                        html=html,
                        metadata={"page": page_num + 1, "rows": len(table_data), "cols": len(table_data[0])},
                    ))

    return elements #返回一个 Element 对象的列表，每个对象包含了文本内容和元数据（如页码、表格行列数等）


def _is_heading(line: str) -> bool:
    """判断是否为标题行"""
    return (line.endswith("：") or line.endswith(":") or
            line.startswith("一、") or line.startswith("二、") or
            line.startswith("三、") or line.startswith("四、")) #简单的中文标题判断逻辑，实际可以更复杂（字体大小、加粗等）

def _is_list_item(line: str) -> bool:
    """判断是否为列表项"""
    return any(line.startswith(f"{i}.") for i in range(1, 10))

def _create_element(elem_type: str, text: str, page_num: int) -> Element: 
    """根据类型创建元素"""
    metadata = {"page": page_num + 1}
    if elem_type == "heading":
        return Title(text=text, metadata=metadata)
    elif elem_type == "list":
        return ListItem(text=text, metadata=metadata)
    else:
        return NarrativeText(text=text, metadata=metadata) #默认当做正文文本处理

def _table_to_markdown(table: list[list]) -> str:
    """表格转 Markdown"""
    if not table or len(table) < 2:
        return ""
    headers = table[0]
    md = ["| " + " | ".join(str(h) if h else "" for h in headers) + " |"]
    md.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in table[1:]:
        md.append("| " + " | ".join(str(cell) if cell else "" for cell in row) + " |")
    return "\n".join(md)

def _table_to_html(table: list[list]) -> str:
    """表格转 HTML（对标 Unstructured 的 text_as_html）"""
    if not table:
        return ""
    html = ["<table>"]
    html.append("<tr>" + "".join(f"<th>{h}</th>" for h in table[0]) + "</tr>")
    for row in table[1:]:
        html.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
    html.append("</table>")
    return "\n".join(html)


# ========== 3. 打印解析结果 ==========
def print_elements(elements: list[Element]):
    """打印解析结果（对标 Unstructured 的输出格式）"""
    print(f"\n解析结果：共 {len(elements)} 个元素\n")

    # 类型统计
    type_counts = {}
    for elem in elements:
        t = type(elem).__name__
        type_counts[t] = type_counts.get(t, 0) + 1

    print("元素类型统计：")
    for t, count in type_counts.items():
        print(f"  {t}: {count} 个")

    # 详细列表
    print(f"\n{'─' * 60}")
    print("详细元素列表：")
    print(f"{'─' * 60}")

    for i, elem in enumerate(elements):
        t = type(elem).__name__
        content = elem.text[:100].replace("\n", " ")
        emoji_map = {"Title": "📌", "NarrativeText": "📝", "Table": "📊", "ListItem": "📋"}
        emoji = emoji_map.get(t, "❓")

        if isinstance(elem, Table):
            print(f"\n  [{i+1}] {emoji} {t}")
            print(f"      内容: {content}...")
            if elem.html:
                print(f"      HTML: {elem.html[:200]}...")
        else:
            print(f"  [{i+1}] {emoji} {t}: {content}")


# ========== 4. 表格深度分析 ==========
def analyze_tables(elements: list[Element]):
    """专门分析表格元素"""
    tables = [e for e in elements if isinstance(e, Table)]
    print(f"\n{'=' * 60}")
    print(f"【表格深度分析】发现 {len(tables)} 个表格")
    print(f"{'=' * 60}")

    for i, table in enumerate(tables):
        print(f"\n表格 {i + 1}:")
        print(f"  Markdown:\n{table.text}")
        print(f"  HTML:\n{table.html}")
        print(f"  元数据: {table.metadata}")


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        # Step 1: 创建示例 PDF
        create_sample_pdf()

        # Step 2: 按元素类型解析（对标 partition_pdf）
        elements = partition_pdf(str(PDF_PATH))

        # Step 3: 打印解析结果
        print_elements(elements)

        # Step 4: 表格深度分析
        analyze_tables(elements)

        print(f"\n{'=' * 60}")
        print("[OK] 复杂文档解析演示完成！")
        print("核心收获：")
        print("  1. 按元素类型解析（Title/Table/ListItem/NarrativeText）")
        print("  2. 表格整体保留，转 Markdown/HTML 保留结构")
        print("  3. 与 TextSplitter 的本质区别：识别结构 vs 按字符切")
        print()
        print("注：本 demo 用 pdfplumber 实现了 Unstructured partition_pdf 的核心逻辑。")
        print("    Unstructured 在 Windows 上 PyTorch/onnxruntime 依赖冲突严重，")
        print("    生产环境建议在 Linux Docker 中使用。")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
