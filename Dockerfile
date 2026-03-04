# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Build-time system deps (compilers, headers for pymupdf etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy manifests first for layer-cache efficiency
COPY pyproject.toml poetry.lock ./

# Install directly from pyproject.toml into a prefix we can copy over.
# pip understands PEP 621 [project] natively — no Poetry needed.
RUN pip install --no-cache-dir --prefix=/install .


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Pull only the installed packages from the builder (no compilers in runtime)
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Tell cache.py and start.sh where we are
ENV BOOKS_CACHE_DIR=/data/complete_books \
    DOCKER_ENV=1

# Prepare the cache mount point with correct ownership
RUN mkdir -p /data/complete_books && chown -R appuser:appuser /data /app

USER appuser

# FastAPI + MCP SSE
EXPOSE 8000 8001

ENTRYPOINT ["/bin/bash", "start.sh"]
