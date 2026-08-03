# Repository Guidelines

## Project Structure & Module Organization

This repository is an AI Agent bootcamp organized by week and section. Top-level `Week_1_*` through `Week_6_*` directories contain lesson modules, each usually with a `README.md`, `demo*.py`, study notes, interview-question notes, and optional confusion logs. `Script/` stores quiz and review materials. Root files such as `learning_plan.md`, `progress.md`, `memory.md`, `CLAUDE.md`, and `REASONIX.md` document the curriculum, progress, and assistant-facing conventions. Docker, monitoring, and vector database assets live inside the relevant section directories, for example the Week 5 Grafana section.

## Build, Test, and Development Commands

- `python -m venv .venv` then `.venv\Scripts\Activate.ps1`: create and activate a local environment on Windows.
- `pip install -r requirements.txt`: install the shared Python dependency set.
- `python path\to\demo1_name.py`: run a self-contained lesson demo; prefer the command shown in that section's `README.md`.
- `uvicorn module:app --reload --port 8000`: run FastAPI demos that expose an ASGI app.
- `docker compose up -d`: start local services for sections that include `docker-compose.yml`, such as Milvus or Grafana stacks.
- `.\Week_6_*\run_all_demos.ps1`: run the curated Week 6 demo smoke check.

## Coding Style & Naming Conventions

Use Python 3.10+ and keep demos independently runnable with an `if __name__ == "__main__"` entry point. Follow existing names: directories use `Week_N_Topic/Section_N_Topic`, demos use `demo<N>_<description>.py`, and learning documents keep the established Chinese filenames. Keep examples educational: clear variable names, concise comments for teaching points, and explicit error handling where external services or APIs may fail.

## Testing Guidelines

There is no centralized test suite yet. Validate changes by running the specific demo files you touched and any directly related orchestration script. For FastAPI examples, verify startup and at least one request path. For RAG, vector database, Redis, Celery, or monitoring demos, document required services and run the relevant `docker compose up -d` stack before testing.

## Commit & Pull Request Guidelines

Recent history uses short imperative summaries, sometimes with scoped prefixes such as `feat(Week6-Sec4): ...`. Prefer `type(scope): summary` for feature additions and a direct Chinese or English summary for learning-material updates. Pull requests should describe the changed week/section, list commands run, mention required services or API keys, and include screenshots only for UI, Grafana, or dashboard changes.

## Security & Configuration Tips

Do not commit `.env`, local databases, vector stores, logs, or generated caches; these are already covered by `.gitignore`. Keep API keys in environment variables and note required configuration in the section `README.md`.
