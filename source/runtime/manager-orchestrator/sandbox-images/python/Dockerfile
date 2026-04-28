FROM python:3.12-slim
RUN useradd -m -u 65532 sandbox \
    && apt-get update && apt-get install -y --no-install-recommends build-essential git curl \
    && pip install --no-cache-dir pytest ruff mypy bandit \
    && rm -rf /var/lib/apt/lists/*
USER 65532:65532
WORKDIR /workspace
