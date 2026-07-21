# 基于已有的 naive-rag 镜像扩展，避免重新拉取 Python 基础镜像
FROM naive-rag:latest

WORKDIR /app

# 安装 PyTorch CPU 版
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 安装 RAG 所需的额外依赖
RUN pip install --no-cache-dir \
    pdfplumber \
    pymilvus \
    fastembed \
    rank_bm25 \
    sentence-transformers \
    reportlab

# 复制代码
COPY demo1_advanced_rag.py .

# Milvus 地址（通过 host.docker.internal 访问宿主机）
ENV MILVUS_URI="http://host.docker.internal:19530"

CMD ["python", "demo1_advanced_rag.py"]
