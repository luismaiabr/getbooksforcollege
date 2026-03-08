# ── Stage: full build using Poetry ────────────────────────────────────────
FROM python:3.12-slim AS base

# Install system build dependencies (compilers, libglib2.0-0 for pymupdf, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        curl \
        nodejs \
        npm \
        tesseract-ocr \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry – try system /usr/bin/poetry first, otherwise install via the official installer
# The installer puts Poetry in /opt/poetry and we symlink it to /usr/local/bin/poetry
RUN if [ -x /usr/bin/poetry ]; then \
        ln -s /usr/bin/poetry /usr/local/bin/poetry; \
    else \
        curl -sSL https://install.python-poetry.org | python3 - && \
        ln -s $HOME/.local/bin/poetry /usr/local/bin/poetry; \
    fi

WORKDIR /app

# Copy only the manifests – Poetry will resolve and install all deps
COPY pyproject.toml poetry.lock ./

# In‑container installs should go straight to the system Python (no venv)
ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_NO_ANSI=1

# Install runtime dependencies (no dev deps, no package itself)
RUN poetry install --only main --no-root

# Copy the rest of the source code
COPY . .

# Install MCP server JS dependencies
RUN cd mcp-js && npm install

# Environment for the app – tell start.sh we are inside Docker
ENV BOOKS_CACHE_DIR=/data/complete_books \
    DOCKER_ENV=1

# Create a non‑root user for security and set ownership of the app directory
RUN useradd --create-home --shell /bin/bash appuser
RUN mkdir -p /data/complete_books /app/token_store && chown -R appuser:appuser /app /data

USER appuser

# Expose FastAPI and MCP SSE ports
EXPOSE 8000 8001

ENTRYPOINT ["/bin/bash", "start.sh"]
