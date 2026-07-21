# Section 2: LangChain 核心组件

## 学习目标

- 理解 LangChain 的设计哲学与核心组件
- 掌握 Prompt Templates 模板化提示词
- 掌握 Output Parsers 输出解析
- 理解 LCEL（LangChain Expression Language）链式调用

## 前置知识

- Section 1: FastAPI 基础（路由、Pydantic、异步）
- OpenAI API 基本调用方式

## 学习顺序

1. 先运行 `demo1_prompt_template.py` — 感受 Prompt Templates
2. 再运行 `demo2_output_parser.py` — 学习输出解析
3. 最后运行 `demo3_lcel_chain.py` — 串联整条 LCEL 链

## 代码运行方式

```bash
# 安装依赖
pip install langchain langchain-openai python-dotenv

# 配置 API Key（在项目根目录创建 .env 文件）
echo OPENAI_API_KEY=你的key > .env

# 依次运行
python demo1_prompt_template.py
python demo2_output_parser.py
python demo3_lcel_chain.py
```

## 注意事项

- LangChain 版本迭代快，本教程基于 v0.2+ 稳定版
- API Key 不要硬编码，统一用 `.env` + `dotenv` 管理
- 如果没有 OpenAI Key，可以用免费的 Ollama 本地模型替代

## 推荐复习内容

- LangChain 官方文档：https://python.langchain.com/
- LCEL 文档：https://python.langchain.com/docs/expression_language/

## 下一节预告

**Section 3: RAG 文档加载与分块策略** — 多格式文档加载、文本分块算法
