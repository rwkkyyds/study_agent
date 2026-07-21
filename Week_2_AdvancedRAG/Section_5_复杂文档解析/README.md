# Section 5: 复杂文档解析（Unstructured）

## 学习目标
1. 理解为什么 Naive RAG 的 TextSplitter 不够用
2. 掌握 Unstructured 库的 `partition_pdf` 解析策略
3. 学会处理 PDF 中的表格、图片、多栏布局
4. 将 Unstructured 解析结果接入 RAG 链路

## 技术栈
- **文档解析**: Unstructured（开源文档解析库，支持 PDF/DOCX/HTML/图片）
- **PDF 创建**: reportlab（生成含表格的示例 PDF）
- **Embedding**: fastembed + BAAI/bge-small-zh-v1.5
- **LLM**: GLM-4-Flash（智谱 API）
- **向量库**: Milvus（Docker 部署）

## 为什么需要 Unstructured？

### Naive RAG 的文档解析问题
```
Week 1 的做法：RecursiveCharacterTextSplitter 按字符数切分
问题：
├── 表格被切碎 → 结构信息丢失
├── 图片被忽略 → 视觉信息丢失
├── 多栏混乱 → 阅读顺序错乱
├── 标题/正文混在一起 → 语义边界模糊
└── 页眉页脚混入 → 噪音数据
```

### Unstructured 的解决方案
| 功能 | Unstructured | TextSplitter |
|------|-------------|-------------|
| 表格识别 | 自动识别，整体保留 | 按字符切碎 |
| 图片处理 | OCR + 版面分析 | 忽略 |
| 元素类型 | Title/Table/ListItem/... | 只有 text |
| 多格式支持 | PDF/DOCX/HTML/图片 | 只有文本 |

## Unstructured 核心 API

### partition_pdf（核心函数）
```python
from unstructured.partition.pdf import partition_pdf

elements = partition_pdf(
    filename="doc.pdf",
    strategy="fast",        # fast / hi_res / ocr_only / auto
    infer_table_structure=True,  # 表格结构推断
    extract_images_in_pdf=True,  # 提取图片
)
```

### 解析策略对比
| 策略 | 速度 | 精度 | 依赖 | 适用场景 |
|------|------|------|------|----------|
| `fast` | 最快 | 中 | 无额外依赖 | 纯文本、简单 PDF |
| `hi_res` | 慢 | 最高 | 需要 OCR 模型 | 复杂 PDF、扫描件 |
| `ocr_only` | 中 | 中 | 需要 Tesseract | 纯扫描件 |
| `auto` | 自动 | 自动 | 根据文档选择 | 不确定类型时 |

### 文档元素类型
Unstructured 将文档解析为结构化元素：
- `Title` — 标题
- `NarrativeText` — 正文段落
- `Table` — 表格（可转 HTML/Markdown）
- `ListItem` — 列表项
- `Image` — 图片
- `Header` / `Footer` — 页眉页脚

## 代码结构

### demo1_unstructured_basics.py
Unstructured 基础解析：
1. 创建示例 PDF（含表格、文本、列表）
2. 使用 `partition_pdf` 解析
3. 查看解析出的元素类型和内容
4. 表格转 HTML/Markdown 保留结构

### demo2_unstructured_rag.py
Unstructured + RAG 集成：
1. Unstructured 解析 PDF → 元素列表
2. 按元素类型分块（表格整体保留）
3. 存入 Milvus 向量库
4. 构建 RAG 链路问答

## 运行方式

```bash
# 安装依赖（已在 .venv 中安装）
pip install unstructured reportlab pymilvus fastembed langchain-openai

# 运行 demo1
python demo1_unstructured_basics.py

# 运行 demo2（需要 Milvus 服务）
docker compose up -d
python demo2_unstructured_rag.py
```

## 注意事项
- `fast` 策略无需额外依赖，推荐先用这个跑通
- `hi_res` 策略需要下载模型，首次运行较慢
- Windows 上 `hi_res` 可能需要额外配置
