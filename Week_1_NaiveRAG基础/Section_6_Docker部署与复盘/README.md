# Section 6: Docker 打包部署 + 第1周 Demo 复盘

## 学习目标
1. 用 Docker 把 RAG API 打包成镜像，一键部署
2. 第1周 Demo：完整 Naive RAG 项目，融合 Section 1-5 所有知识点

## 前置知识
- Section 5 的 RAG API（demo2_rag_api.py）

## 项目结构
```
Section_6_Docker部署与复盘/
├── app.py              # FastAPI RAG 应用（融合第1周全部知识）
├── Dockerfile          # Docker 镜像定义
├── requirements.txt    # Python 依赖
├── .dockerignore       # Docker 构建忽略文件
└── README.md           # 本文件
```

---

## 方式一：本地 Windows 运行（不用 Docker）

```bash
cd Week_1_NaiveRAG基础/Section_6_Docker部署与复盘

# 安装依赖
pip install -r requirements.txt

# 启动
python app.py
```

访问：
- 健康检查：http://127.0.0.1:8000/health
- API 文档：http://127.0.0.1:8000/docs
- 问答测试：http://127.0.0.1:8000/docs 页面点 POST /query → Try it out

---

## 方式二：本地 Windows Docker 运行

```bash
# 1. 启动 Docker Desktop（双击桌面图标或开始菜单搜索）

# 2. 构建镜像
cd Week_1_NaiveRAG基础/Section_6_Docker部署与复盘
docker build -t naive-rag .

# 3. 运行容器
docker run -d -p 8000:8000 naive-rag

# 4. 验证
curl http://127.0.0.1:8000/health
```

---

## 方式三：Ubuntu 虚拟机运行

### 第一步：从本地传文件到虚拟机

在本地 Windows 终端执行（先把项目目录打成压缩包）：
```powershell
# 进入项目根目录
cd C:\Users\rwkkyyds\Desktop\AI_Agent_8Weeks_Bootcamp

# 打包 Section_6 目录（需要先装 tar 或用 PowerShell 压缩）
Compress-Archive -Path "Week_1_NaiveRAG基础\Section_6_Docker部署与复盘" -DestinationPath "Section_6.zip"
```

然后用 SSH 工具（Xshell/MobaXterm/终端）连接虚拟机，在虚拟机中用 `rz` 接收文件：
```bash
# 虚拟机终端中执行
cd ~
rz -y    # -y 覆盖同名文件，弹出文件选择框，选本地的 Section_6.zip
```

解压：
```bash
unzip Section_6.zip -d AI_Agent_Bootcamp
cd AI_Agent_Bootcamp/Section_6_Docker部署与复盘
```

### 第二步：安装 Docker（如果虚拟机没装）

```bash
# 更新包索引
sudo apt update

# 安装 Docker
sudo apt install -y docker.io

# 启动 Docker 并设置开机自启
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version

# 免 sudo 运行 docker（可选，重新登录生效）
sudo usermod -aG docker $USER
```

### 第三步：构建镜像并运行

```bash
# 构建镜像
docker build -t naive-rag .

# 运行容器
docker run -d -p 8000:8000 naive-rag

# 查看运行状态
docker ps
```

### 第四步：验证服务

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 问答测试
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是RAG？"}'

# 浏览器访问（虚拟机 IP 可通过 ip addr 查看）
# http://<虚拟机IP>:8000/docs
```

### 第五步：常用运维命令

```bash
# 查看容器日志
docker logs <container_id>

# 进入容器内部
docker exec -it <container_id> /bin/bash

# 停止容器
docker stop <container_id>

# 删除容器
docker rm <container_id>

# 删除镜像
docker rmi naive-rag
```

### 第六步：从虚拟机传文件回本地（可选）

```bash
# 虚拟机中打包
cd ~
tar czf result.tar.gz AI_Agent_Bootcamp/Section_6_Docker部署与复盘/

# 用 sz 下载到本地
sz result.tar.gz
```

---

## 推荐复习
- Section 1: FastAPI 路由和 Pydantic
- Section 2: LangChain LCEL
- Section 5: RAG 全链路

## 下一节预告
第2周开始：Advanced RAG — Query Transformation、混合检索、Rerank、RAGAs 评估
