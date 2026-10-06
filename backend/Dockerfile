# ---- base: общий слой для всех стадий ----
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# ---- deps: зависимости рантайма (кэшируется, пока requirements.txt не меняется) ----
FROM base AS deps
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install --prefix=/install -r requirements.txt

# ---- test: для make test и CI ----
FROM base AS test
COPY requirements.txt requirements-dev.txt ./
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements-dev.txt
COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY tests ./tests
CMD ["sh", "-c", "ruff check . && ruff format --check . && pytest -q -p no:cacheprovider --cov"]

# ---- runtime: минимальный образ, non-root ----
FROM base AS runtime
RUN groupadd -g 10001 app && useradd -u 10001 -g app -s /usr/sbin/nologin -M app
COPY --from=deps /install /usr/local
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
