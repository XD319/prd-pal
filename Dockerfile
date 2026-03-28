FROM node:22-alpine AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY requirement_review_v1/ ./requirement_review_v1/
COPY review_runtime/ ./review_runtime/
COPY data/ ./data/
COPY main.py pyproject.toml ./
COPY --from=frontend-build /frontend/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "requirement_review_v1.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
