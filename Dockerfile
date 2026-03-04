# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

# System deps needed to compile some Python packages (e.g. pymupdf)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (no venv inside the build, export to requirements instead)
ENV POETRY_VERSION=1.8.5 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

WORKDIR /build

# Copy only the dependency manifests first (layer-cache friendly)
COPY pyproject.toml poetry.lock ./

# Export a plain requirements.txt so the runtime stage stays lean
RUN poetry export --without-hashes --format=requirements.txt -o requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install deps from the exported requirements
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source
COPY . .

# The cache directory sits at ../../temp/complete_books relative to the source.
# Inside the container we keep everything under /app, so we pin the base path
# to /data/complete_books (mounted as a volume at runtime).
ENV BOOKS_CACHE_DIR=/data/complete_books \
    DOCKER_ENV=1

# Make the cache directory and give ownership to appuser
RUN mkdir -p /data/complete_books && chown -R appuser:appuser /data /app

USER appuser

# Expose FastAPI and MCP ports
EXPOSE 8000 8001

# Entrypoint: start both servers using the shell script
ENTRYPOINT ["/bin/bash", "start.sh"]
