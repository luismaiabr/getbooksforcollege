#!/usr/bin/env bash
# start.sh — Start FastAPI server and MCP SSE server
# Reads configuration from .env in the project root

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env variables only for local dev runs.
# Inside Docker the vars are injected by docker-compose env_file — no file needed.
if [ "${DOCKER_ENV:-0}" = "1" ]; then
    : # env already set by docker-compose
elif [ -f ".env" ]; then
    export $(grep -v '^\s*#' .env | grep -v '^\s*$' | xargs)
else
    echo "ERROR: .env file not found in $SCRIPT_DIR"
    exit 1
fi

# Derive host/port for FastAPI from BASE_URL (e.g. http://127.0.0.1:8000)
FASTAPI_HOST="${BASE_URL#http://}"
FASTAPI_HOST="${FASTAPI_HOST#https://}"
FASTAPI_PORT="${FASTAPI_HOST##*:}"
FASTAPI_HOST="${FASTAPI_HOST%%:*}"

# Fallback defaults
FASTAPI_HOST="${FASTAPI_HOST:-127.0.0.1}"
FASTAPI_PORT="${FASTAPI_PORT:-8000}"
MCP_SERVER_ADDRESS="${MCP_SERVER_ADDRESS:-127.0.0.1}"
MCP_SERVER_PORT="${MCP_SERVER_PORT:-8001}"

echo "=============================="
echo "  Book Gateway — Starting Up  "
echo "=============================="
echo "FastAPI  → http://${FASTAPI_HOST}:${FASTAPI_PORT}"
echo "MCP SSE  → http://${MCP_SERVER_ADDRESS}:${MCP_SERVER_PORT}/sse"
echo ""

# Inside Docker, Poetry is not installed — packages are on the system PATH.
# Locally, use `poetry run` to pick up the virtualenv.
if [ "${DOCKER_ENV:-0}" = "1" ]; then
    FASTAPI_HOST="0.0.0.0"
    FASTAPI_PORT="8000"
    MCP_SERVER_ADDRESS="0.0.0.0"
    RELOAD_FLAG=""
    RUN_PREFIX=""
else
    RELOAD_FLAG="--reload"
    RUN_PREFIX="poetry run"
fi

export FASTAPI_HOST MCP_SERVER_ADDRESS BASE_URL FASTAPI_PORT

# Start FastAPI
$RUN_PREFIX uvicorn main:app \
    --host "$FASTAPI_HOST" \
    --port "$FASTAPI_PORT" \
    $RELOAD_FLAG &
FASTAPI_PID=$!
echo "[FastAPI] started (PID $FASTAPI_PID)"

# Give FastAPI a moment to bind before MCP tries to connect
sleep 2

# Start MCP SSE server
$RUN_PREFIX python3 mcp/server.py &
MCP_PID=$!
echo "[MCP]     started (PID $MCP_PID)"

echo ""
echo "Both servers are running. Press Ctrl+C to stop."

# Trap Ctrl+C and kill both processes cleanly
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill "$FASTAPI_PID" 2>/dev/null || true
    kill "$MCP_PID" 2>/dev/null || true
    wait "$FASTAPI_PID" 2>/dev/null || true
    wait "$MCP_PID" 2>/dev/null || true
    echo "Done."
}
trap cleanup INT TERM

# Wait for both background jobs to finish (or Ctrl+C)
wait
