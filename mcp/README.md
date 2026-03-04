# Book Gateway MCP Server — Client Guide

The MCP server is already running as part of the Book Gateway deployment.
This guide explains how to connect your AI client to it.

## Prerequisites

The server is only reachable through the **Tailscale VPN**. Make sure you are connected before trying to use it.

## SSE Endpoint

```
http://100.101.78.95:8002/sse
```

> All MCP tools are served over this single SSE endpoint. No local setup required.

---

## Connecting Your Client

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "book-gateway": {
      "transport": "sse",
      "url": "http://100.101.78.95:8002/sse"
    }
  }
}
```

### Cursor (`~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "book-gateway": {
      "transport": "sse",
      "url": "http://100.101.78.95:8002/sse"
    }
  }
}
```

### Any other MCP-compatible client

Set the transport to **SSE** and point it to `http://100.101.78.95:8002/sse`.

---

## Available Tools

Once connected, your AI client has access to the following tools:

| Tool | Description |
|---|---|
| `list_books()` | Lists all PDF books in the Google Drive folder with their IDs and names. |
| `get_book_content(file_id)` | Returns the full text of a book, page by page. Triggers a lazy-download from Drive if not yet cached. |
| `request_excerpt(file_id, start_page, end_page)` | Queues an excerpt generation job for the given page range. Returns a `job_id`. |
| `check_job_status(job_id)` | Checks whether an excerpt job is pending, ready, or failed. |
| `check_job_download(job_id)` | Confirms the excerpt PDF has been saved on the server. |
