# Book Gateway MCP Server

This directory contains a Model Context Protocol (MCP) server that exposes tools to seamlessly interact with the FastAPI Book Gateway endpoints using AI Models and Agents.

## Configuration

Since the MCP server acts as an interface that speaks to the actual FastAPI Backend, it needs to point to the address where your FastAPI is running, as well as define its own host/port if using SSE (Server-Sent Events) mode.

The variables inside your root `.env` configure this:

```env
# Address of the *FastAPI* server
BASE_URL=http://127.0.0.1:8000

# MCP Server Config
MCP_SERVER_ADDRESS=127.0.0.1
MCP_SERVER_PORT=8001
```

## Running the MCP Server

Ensure that your FastAPI backend is running first:

```bash
poetry run uvicorn main:app --reload --port 8000
```

Then start the MCP server using SSE mode on the specified port:

```bash
poetry run uvicorn mcp.server:mcp._app --host 127.0.0.1 --port 8001
# Or run it directly:
poetry run python mcp/server.py
```

> **Note on Transport:** The server script calls `mcp.run(transport='sse', host=..., port=...)` to bind it locally. Modern MCP clients (like Claude Desktop) may alternatively spawn this via `stdio` directly.

## Available Tools

The MCP Server automatically exposes the following functions to AI Agents:

- `list_books()`: Maps to `GET /books`. Shows all available books and their IDs.
- `get_book_content(file_id)`: Maps to `GET /books/{file_id}/content`. Reads the entirety of a book page by page. Lazy-downloads and chunks if needed.
- `request_excerpt(file_id, start_page, end_page)`: Maps to `POST /books/{file_id}/excerpt`. Triggers the background fat-PDF slicing engine and dispatches an email. Returns a Job ID.
- `check_job_status(job_id)`: Maps to `GET /jobs/{job_id}/status`. Check if an excerpt job is finished.
- `check_job_download(job_id)`: Maps to `GET /jobs/{job_id}/download`. Verifies server excerpt disk save completion.
