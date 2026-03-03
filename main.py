"""FastAPI Book Gateway — entry point."""

import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers import books, content, jobs
from services import cache, drive, pdf_processor, renamer_job


def _process_all_books_task() -> None:
    """Background task that downloads and extracts text for all books if missing."""
    print("Background pre-computation started...")
    try:
        drive_books = drive.list_books()
        for b in drive_books:
            book_name = b["name"]
            pdf_path = cache.get_pdf_path(book_name)
            content_path = cache.get_content_path(book_name)

            if not (content_path.exists() and content_path.stat().st_size > 0):
                print(f"Pre-computing missing content for: {book_name}")
                if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                    try:
                        drive.download_book(b["id"], pdf_path)
                    except Exception as exc:
                        print(f"Failed to download {book_name}: {exc}")
                        continue
                try:
                    pdf_processor.build_content_json(book_name, pdf_path, content_path)
                    print(f"Successfully processed {book_name}")
                except Exception as exc:
                    print(f"Failed to parse {book_name}: {exc}")
    except Exception as exc:
        print(f"Background task failed: {exc}")
    print("Background pre-computation finished.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Authenticating with Google Drive...")
    try:
        # Force authentication on startup so both background tasks don't try to auth at the same time
        drive._get_drive_service()
        print("Google Drive authenticated successfully.")
    except Exception as exc:
        print(f"Failed to authenticate with Google Drive: {exc}")

    # Start the processing function in a daemon thread so it doesn't block FastAPI startup
    thread = threading.Thread(target=_process_all_books_task, daemon=True)
    thread.start()
    
    # Start the async LLM renaming loop
    renamer_task = asyncio.create_task(renamer_job.renaming_loop())
    
    yield
    
    # Teardown
    renamer_task.cancel()


app = FastAPI(
    title="Book Gateway API",
    description="On-demand access to PDF books stored in Google Drive.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(books.router)
app.include_router(content.router)
app.include_router(jobs.router)
