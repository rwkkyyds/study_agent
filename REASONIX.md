---
permissionMode: bypassPermissions
---
# REASONIX.md

## Stack
- **Python 3.10+** — no `pyproject.toml`; each Section pins deps in its own `requirements.txt`
- **FastAPI** — primary web framework; all services use `uvicorn` as server
- **LangChain + LangGraph** — AI orchestration; `StateGraph`, `ToolNode`, `create_agent`
- **SQLAlchemy 2.0** — ORM layer over PostgreSQL; `DeclarativeBase`, Session DI
- **Redis** — caching (Cache-Aside), session store, sliding-window rate limiter, Pub/Sub
- **Docker + Compose** — deployment; Milvus runs via `docker-compose.yml`

## Layout
- `Week_1_NaiveRAG基础/` through `Week_7_8_工业级项目/` — curriculum by week; each week has `Section_N_Topic/`
- `Script/` — quiz scripts and answer keys
- `models/` — cached HuggingFace models (`bge-reranker-base`, ONNX variants)
- `.venv/` — Python virtual environment (gitignored)
- `chroma_data/` — local Chroma vector store (persisted on disk)

## Commands
- **Run a demo:** `python <Section>/demo<N>_<name>.py` (every demo is self-contained with `if __name__ == "__main__"`)
- **Start Milvus:** `docker-compose up -d` (in `Week_2_AdvancedRAG/Section_4_Milvus向量库/`)
- **Build Docker image (Week1):** `docker build -t naive-rag . && docker run -p 8000:8000 naive-rag`
- **No build / test / lint / typecheck scripts** — this is a learning project, not a library

## Conventions
- **All content in Chinese** — README, code comments, learning notes, quiz materials
- **Demo naming:** `demo{N}[a-z]_{feature}_{layer}.py` — e.g. `demo2a_retry_tenacity_basics.py`; a/b/c = learning progression
- **Section file set:** `README.md` + `demo*.py` + `学习笔记.md` + `生产级高频面试题.md` + `不理解的部分.md`
- **Code rules per memory.md:** try-except + logging + Pydantic enforced; single demo ≤350 lines; split by feature not line count
- **LLM backend:** DeepSeek API (`api.deepseek.com`) via `langchain-openai` compatible interface
- **Embedding:** `fastembed` (local BGE models) preferred over paid API embeddings

## Watch out for
- **No `pyproject.toml` / `setup.py`** — dependencies live in per-Section `requirements.txt` files; there is no single `pip install` for the whole project
- **Each demo is designed to run standalone from its own directory** — relative paths (e.g. `"./chroma_data"`) assume CWD is the Section folder
- **PostgreSQL connection:** defaults to `postgresql://postgres:123456@localhost:5432/postgres` across all demos
- **Models/ is a HuggingFace cache, not source code** — don't edit; `fastembed` auto-downloads here
- **`memory.md` is the teaching syllabus, not project metadata** — it defines pedagogy rules (one Section at a time, quiz every 3 Sections, etc.)
