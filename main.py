"""FastAPI Book Gateway — entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers import books, content, jobs, excerpts
from services import cache, drive, pdf_processor, renamer_job, preprocessor





@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Authenticating with Google Drive...")
    try:
        # Force authentication on startup so both background tasks don't try to auth at the same time
        drive._get_drive_service()
        print("Google Drive authenticated successfully.")
    except Exception as exc:
        print(f"Failed to authenticate with Google Drive: {exc}")

    # Start the async LLM renaming loop and the async content extraction loop
    preprocessor_task = asyncio.create_task(preprocessor.content_extraction_loop())
    renamer_task = asyncio.create_task(renamer_job.renaming_loop())
    
    yield
    
    # Teardown
    preprocessor_task.cancel()
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
app.include_router(excerpts.router)


@app.get("/health")
async def health():
    """Lightweight liveness check — no Drive auth required."""
    return {"status": "ok"}
