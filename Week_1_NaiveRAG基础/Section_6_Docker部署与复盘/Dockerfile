# 基础镜像：Python 3.12 slim（轻量版，不含多余工具）
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层（依赖不变时不用重新安装）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 
# 复制应用代码
COPY app.py .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
