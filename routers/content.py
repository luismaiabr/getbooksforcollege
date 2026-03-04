"""Router for /books/{file_id}/content and /books/{file_id}/excerpt."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from schemas.whole_book import Book, PageContent, ExcerptRequest, ExcerptResponse
from services import cache, drive, email_service, jobs as job_store, pdf_processor
from services.jobs import JobStatus

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

router = APIRouter(prefix="/books", tags=["content"])


def _resolve(file_id: str) -> tuple[str, Path, Path]:
    """Resolve file_id → (book_name, pdf_path, content_path). Raises HTTPException on error."""
    try:
        meta = drive.get_book_metadata(file_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Book ID '{file_id}' not found in Drive: {exc}") from exc
    book_name = meta["name"]
    return book_name, cache.get_pdf_path(book_name), cache.get_content_path(book_name)


# ── GET /books/{file_id}/content ─────────────────────────────────────────────

@router.get("/{file_id}/content", response_model=Book)
async def get_content(file_id: str):
    """
    Return full text of the book, page by page.
    Uses cached content.json if available; otherwise downloads from Drive,
    extracts text, and caches the result.
    """
    book_name, pdf_path, content_path = _resolve(file_id)

    if content_path.exists() and content_path.stat().st_size > 0:
        data = json.loads(content_path.read_text(encoding="utf-8"))
        return Book(**data)

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        try:
            drive.download_book(file_id, pdf_path)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Drive download error: {exc}") from exc

    try:
        pages: list[PageContent] = pdf_processor.build_content_json(book_name, pdf_path, content_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF processing error: {exc}") from exc

    return Book(pages=pages)


# ── GET /books/{book_id}/content-only ────────────────────────────────────────

@router.get("/{book_id}/content-only")
async def get_content_only(book_id: str):
    """
    Return the raw content.json file for download.
    Lazy: if content.json doesn't exist, downloads the PDF from Drive,
    extracts text, generates content.json, then serves it.
    """
    book_name, pdf_path, content_path = _resolve(book_id)

    if not (content_path.exists() and content_path.stat().st_size > 0):
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            try:
                drive.download_book(book_id, pdf_path)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Drive download error: {exc}") from exc

        try:
            pdf_processor.build_content_json(book_name, pdf_path, content_path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"PDF processing error: {exc}") from exc

    return FileResponse(
        path=str(content_path),
        media_type="application/json",
        filename=f"{book_name}_content.json",
    )


# ── POST /books/{file_id}/excerpt ─────────────────────────────────────────────


def _run_excerpt_job(job_id: str, file_id: str, book_name: str, start: int, end: int) -> None:
    """Background task: download (if needed), slice PDF, mark job done."""
    try:
        pdf_path = cache.get_pdf_path(book_name)
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            drive.download_book(file_id, pdf_path)

        buffer = pdf_processor.slice_pdf(pdf_path, start, end)

        out_path: Path = cache.get_excerpt_path(book_name, start, end)
        out_path.write_bytes(buffer.read())

        job_store.set_ready(job_id, out_path)
    except Exception as exc:  # noqa: BLE001
        job_store.set_error(job_id, str(exc))


@router.post("/{file_id}/excerpt", response_model=ExcerptResponse)
async def get_excerpt(file_id: str, body: ExcerptRequest, background_tasks: BackgroundTasks):
    """
    Start background excerpt generation. Sends email immediately with progress
    and download links, and returns those same links in the response.
    """
    book_name, _, _ = _resolve(file_id)

    job_id = book_name
    job_store.create_or_reset(job_id)

    status_url = f"{BASE_URL}/jobs/{job_id}/status"
    download_url = f"{BASE_URL}/jobs/{job_id}/download"
    file_url = f"{BASE_URL}/jobs/{job_id}/file"

    background_tasks.add_task(_run_excerpt_job, job_id, file_id, book_name, body.start, body.end)

    try:
        email_service.send_excerpt_email(
            book_name=book_name,
            start=body.start,
            end=body.end,
            status_url=status_url,
            file_url=file_url,
        )
        email_error = None
    except Exception as exc:  # noqa: BLE001
        email_error = str(exc)

    return {
        "job_id": job_id,
        "book_name": book_name,
        "status": JobStatus.PENDING,
        "status_url": status_url,
        "download_url": download_url,
        "file_url": file_url,
        "email_sent": email_error is None,
        "email_error": email_error,
    }
