"""Router for /books/{file_id}/content and /books/{file_id}/excerpt."""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import Response

from schemas.whole_book import Book, PageContent, ExcerptRequest, ExcerptResponse
from services import cache, db, drive, email_service, jobs as job_store, pdf_processor, summary_service
from services.jobs import JobStatus

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

router = APIRouter(prefix="/books", tags=["content"])


def _resolve(file_id: str) -> tuple[str, str, Path]:
    """Resolve file_id → (book_name, folder_name, pdf_path). Raises HTTPException on error."""
    try:
        meta = drive.get_book_metadata(file_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Book ID '{file_id}' not found in Drive: {exc}") from exc
    book_name = meta["name"]
    folder_name = meta.get("folder", "")
    return book_name, folder_name, cache.get_pdf_path(book_name)


def _to_page_models(content: list[dict]) -> list[PageContent]:
    return [PageContent.model_validate(page) for page in content]


async def _get_or_extract_content(file_id: str, book_name: str, folder_name: str, pdf_path: Path) -> list[dict]:
    stored_content = db.get_book_content(file_id)
    if stored_content is not None:
        return stored_content

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        try:
            drive.download_book(file_id, pdf_path)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Drive download error: {exc}") from exc

    try:
        loop = asyncio.get_running_loop()
        content, _ = await loop.run_in_executor(None, pdf_processor.extract_book_content, pdf_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF processing error: {exc}") from exc

    try:
        db.save_book_content(file_id, book_name, folder_name, content)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Database error: {exc}") from exc

    return content


# ── GET /books/{file_id}/content ─────────────────────────────────────────────

@router.get("/{file_id}/content", response_model=Book)
async def get_content(file_id: str):
    """
    Return full text of the book, page by page.
    Uses Supabase content if available; otherwise downloads from Drive,
    extracts text, stores it in Supabase, and returns it.
    """
    book_name, folder_name, pdf_path = _resolve(file_id)
    content = await _get_or_extract_content(file_id, book_name, folder_name, pdf_path)
    return Book(pages=_to_page_models(content))


# ── GET /books/{book_id}/content-only ────────────────────────────────────────

@router.get("/{book_id}/content-only")
async def get_content_only(book_id: str):
    """
    Return the raw book content JSON for download.
    Lazy: if content is not stored in Supabase yet, downloads the PDF from Drive,
    extracts text, stores it in Supabase, then serves it.
    """
    book_name, folder_name, pdf_path = _resolve(book_id)
    content = await _get_or_extract_content(book_id, book_name, folder_name, pdf_path)
    payload = json.dumps({"pages": content}, ensure_ascii=False, indent=2)

    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{book_name}_content.json"'},
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
    Start background excerpt generation. Generates a summary from the excerpt
    text, sends email with summary, saves everything to DB, and returns links.
    """
    book_name, folder_name, pdf_path = _resolve(file_id)

    job_id = book_name
    job_store.create_or_reset(job_id)

    status_url = f"{BASE_URL}/jobs/{job_id}/status"
    download_url = f"{BASE_URL}/jobs/{job_id}/download"
    file_url = f"{BASE_URL}/jobs/{job_id}/file"

    background_tasks.add_task(_run_excerpt_job, job_id, file_id, book_name, body.start, body.end)

    # Generate summary from the book content for the requested pages
    summary = ""
    try:
        content = await _get_or_extract_content(file_id, book_name, folder_name, pdf_path)
        # content is list[dict] with keys "page" (1-indexed) and "text"
        excerpt_pages = [p for p in content if isinstance(p, dict) and body.start <= p.get("page", 0) <= body.end]
        excerpt_text = "\n\n".join(p.get("text", "") for p in excerpt_pages)
        if excerpt_text.strip():
            summary = await summary_service.generate_excerpt_summary(excerpt_text)
            print(f"[Excerpt] Generated summary for '{book_name}' pages {body.start}-{body.end}")
    except Exception as exc:
        print(f"[Excerpt] Summary generation failed for '{book_name}': {exc}")

    # Automatically save to excerpts table
    try:
        db.save_excerpt(
            file_id=file_id,
            start_page=body.start,
            end_page=body.end,
            has_been_studied=False,
            resource_link=file_url,
            how_many_times_reviewd=0,
            summary=summary or None,
        )
    except Exception as exc:
        print(f"Failed to auto-save excerpt to DB: {exc}")

    try:
        email_service.send_excerpt_email(
            book_name=book_name,
            start=body.start,
            end=body.end,
            status_url=status_url,
            file_url=file_url,
            summary=summary,
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
