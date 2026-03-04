# Book Gateway API

A FastAPI gateway that serves PDF books stored in **Google Drive** on-demand — without permanently keeping files in memory or exposing Drive directly to clients. Books are downloaded lazily, text is extracted and cached locally, and page excerpts are generated in the background with email notifications.

---

## Architecture

```
Client
  │
  ▼
FastAPI (main.py)
  ├── GET  /books                         → lists Drive folder
  ├── POST /books/rename/{file_id}        → updates local name override
  ├── GET  /books/{file_id}/content       → full text (lazy download + cache)
  ├── GET  /books/{file_id}/content-only  → raw content.json (lazy download + cache)
  ├── POST /books/{file_id}/excerpt       → starts background job + sends email
  ├── GET  /jobs/{job_id}/status          → checks job progress
  └── GET  /jobs/{job_id}/download        → confirms excerpt is ready (no PDF bytes)

Services
  ├── drive.py          → Google Drive API (list, metadata, download by file_id)
  ├── cache.py          → temp/ folder management + name override map
  ├── pdf_processor.py  → text extraction (PyMuPDF) + page slicing (pypdf)
  ├── email_service.py  → SMTP email with status/download links
  └── jobs.py           → in-memory job store (pending / ready / error)
```

---

## Running

```bash
# From the project root (WSL or Linux):
poetry run uvicorn main:app --reload --port 8000
```

Interactive docs: `http://localhost:8000/docs`

### MCP Integration

This project includes a fully functional Model Context Protocol (`mcp`) server, letting AI Agents interact with all endpoints directly.
Read the [MCP documentation in `mcp/README.md`](mcp/README.md) for how to use it.

---

## Environment Variables (`.env`)

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Google Cloud API key with Drive API enabled |
| `GOOGLE_DRIVE_FOLDER_ID` | ID of the Drive folder containing the PDFs |
| `SMTP_HOST` | SMTP server host (e.g. `smtp.hostinger.com`) |
| `SMTP_PORT` | SMTP port — `465` for SSL, `587` for STARTTLS |
| `SMTP_USER` | SMTP login (sender email address) |
| `SMTP_PASSWORD` | SMTP password |
| `TARGET_EMAIL` | Recipient for all outgoing emails |
| `BASE_URL` | Public base URL of this API (used to build links in emails) |

> **Note:** `.env` is gitignored. Never commit it.

---

## Routes

### Data Models (Schemas)

The API uses the following primary Pydantic models:

**`DriveBook`** (returned by `GET /books`)
```json
{
  "id": "string",
  "name": "string",
  "has_been_renamed": "boolean",
  "categories": ["string"],
  "is_available": "boolean"
}
```

**`Book`** and **`PageContent`** (returned by `GET /books/{file_id}/content`)
```json
{
  "pages": [
    {
      "page": "integer",
      "text": "string"
    }
  ]
}
```

**`ExcerptRequest`** (accepted by `POST /books/{file_id}/excerpt`)
```json
{
  "start": "integer",
  "end": "integer"
}
```

**`ExcerptResponse`** (returned by `POST /books/{file_id}/excerpt`)
```json
{
  "job_id": "string",
  "book_name": "string",
  "status": "string (pending|ready|error)",
  "status_url": "string (url)",
  "download_url": "string (url)",
  "file_url": "string (url)",
  "email_sent": "boolean",
  "email_error": "string | null"
}
```

---

### `GET /books`

Lists all PDF files in the configured Drive folder.

**Response** `200`:
```json
[
  {
    "id": "1AT2hni...",
    "name": "Designing Data-Intensive Applications - Kleppmann",
    "has_been_correctly_renamed": true,
    "categories": ["computer science", "databases", "systems design"],
    "is_available": true
  },
  {
    "id": "1vDOqgp...",
    "name": "TESTES",
    "has_been_correctly_renamed": false,
    "categories": [],
    "is_available": false
  }
]
```

`has_been_renamed: true` means the book has been successfully processed by the AI and renamed in Google Drive. Books not yet processed will show `false`.

`is_available: true` means `content.json` is ready locally. The API runs a **background worker on startup** that automatically downloads and processes missing books, making them available asynchronously.


### `GET /books/{file_id}/content`

Returns the full text of the book as a structured JSON, page by page.

**Lazy loading:**
1. If `content.json` is cached → served immediately
2. If not, the PDF is downloaded from Drive → text extracted → `content.json` saved → response returned

**Response** `200`:
```json
{
  "pages": [
    { "page": 1, "text": "Distributed Systems\nMaarten van Steen..." },
    { "page": 2, "text": "Cover art by Max van Steen..." }
  ]
}
```

---

### `GET /books/{book_id}/content-only`

Returns the raw `content.json` file as a downloadable JSON file. Same lazy behaviour as `/content`.

**Response** `200`: raw JSON file download  
**Filename:** `{Book Name}_content.json`

Use this route when you need the file directly (e.g., to pass to another tool) rather than the parsed Pydantic model.

---

### `POST /books/{file_id}/excerpt`

Triggers an excerpt generation job (background). Immediately:
- Returns job links in the response
- Sends an email to `TARGET_EMAIL` with status and download links

**Body (`ExcerptRequest`):**
```json
{ "start": 10, "end": 25 }
```

Pages are **1-indexed, inclusive** on both ends.

**Response** `200`:
```json
{
  "job_id": "Distributed Systems - Tanenbaum",
  "book_name": "Distributed Systems - Tanenbaum",
  "status": "pending",
  "status_url": "http://127.0.0.1:8000/jobs/Distributed Systems - Tanenbaum/status",
  "download_url": "http://127.0.0.1:8000/jobs/Distributed Systems - Tanenbaum/download",
  "file_url": "http://127.0.0.1:8000/jobs/Distributed Systems - Tanenbaum/file",
  "email_sent": true,
  "email_error": null
}
```

The background job: downloads the PDF (if not cached) → slices pages → saves to `excerpts/{start}-{end}.pdf`.

---

### `GET /jobs/{job_id}/status`

Polls the status of an excerpt generation job.

**Response** `200`:
```json
{ "job_id": "...", "status": "pending" | "ready" | "error", "error": null }
```

---

### `GET /jobs/{job_id}/download`

Confirms the excerpt is ready. **Does not return PDF bytes** — the file is saved on the server at `temp/complete_books/{book}/excerpts/{start}-{end}.pdf`.

**Response** `200` (ready):
```json
{
  "job_id": "...",
  "status": "ready",
  "filename": "10-25.pdf",
  "message": "Excerpt is ready and saved on the server."
}
```

**Response** `200` (still processing):
```json
{ "job_id": "...", "status": "pending", "message": "Still processing. Try again shortly." }
```

> The email sent by `/excerpt` contains a link to this endpoint so you can check when the excerpt is done.

---

### `GET /jobs/{job_id}/file`

Downloads the actual generated PDF file bytes for the excerpt. Returns `202 Accepted` if the job is still processing.


---

## Local Cache Structure

```
temp/
└── complete_books/
    └── {Book Name}/
        ├── {Book Name}.pdf           ← full book (downloaded on demand)
        ├── content.json              ← extracted text (generated on demand)
        └── excerpts/
            └── {start}-{end}.pdf    ← sliced PDFs
```

---

## Tech Stack

| Concern | Library |
|---|---|
| API framework | FastAPI + uvicorn |
| Model Context Protocol | `mcp`, `FastMCP` |
| Google Drive | google-api-python-client + google-auth |
| PDF text extraction | PyMuPDF (`fitz`) |
| PDF page slicing | pypdf |
| Email | stdlib `smtplib` (SSL port 465 or STARTTLS 587) |
| Env vars | python-dotenv |

---

## Limitations

- **Google Drive API** — Access is via OAuth 2.0 to allow automated renaming of the remote files.
- **Job store** — in-memory only. Jobs are lost on server restart (excerpt PDFs remain on disk).
- **No auth** — all routes are public. Add OAuth/JWT middleware before exposing externally.