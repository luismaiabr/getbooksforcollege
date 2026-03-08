"""FastAPI Book Gateway — entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers import books, content, jobs, excerpts, tasks, roadmap
from services import drive, renamer_job, roadmap_sync





@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Authenticating with Google Drive...")
    try:
        # Force authentication on startup so both background tasks don't try to auth at the same time
        drive._get_drive_service()
        print("Google Drive authenticated successfully.")
    except Exception as exc:
        print(f"Failed to authenticate with Google Drive: {exc}")

    # Start the async background services.
    renamer_task = asyncio.create_task(renamer_job.renaming_loop())
    roadmap_task = asyncio.create_task(roadmap_sync.sync_loop())
    
    # Start recurring task background services
    from services import background_tasks
    task_gen_task = asyncio.create_task(background_tasks.repeated_task_generation_service())
    task_check_task = asyncio.create_task(background_tasks.check_repeating_tasks())
    
    yield
    
    # Teardown
    renamer_task.cancel()
    roadmap_task.cancel()
    task_gen_task.cancel()
    task_check_task.cancel()


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
app.include_router(tasks.router)
app.include_router(roadmap.router)


@app.get("/health")
async def health():
    """Lightweight liveness check — no Drive auth required."""
    return {"status": "ok"}
