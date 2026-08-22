# AI 面试官系统 Dockerfile：前端构建产物由 FastAPI /web 托管。

FROM node:20-alpine AS frontend-builder

WORKDIR /src

COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

COPY frontend/ ./frontend/
RUN cd frontend && npm run build


FROM python:3.11-slim AS python-builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.11-slim

ENV PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=python-builder /root/.local /root/.local
COPY app/ ./app/
COPY --from=frontend-builder /src/app/web ./app/web
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')" || exit 1

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
