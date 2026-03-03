"""Router for job status endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services import jobs as job_store
from services.jobs import JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/status")
async def job_status(job_id: str):
    """Return the current status of an excerpt generation job."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return {"job_id": job.job_id, "status": job.status, "error": job.error}


@router.get("/{job_id}/download")
async def download_result(job_id: str):
    """
    Confirm the excerpt is ready. Does NOT return the PDF bytes —
    the file is processed and saved internally on the server.
    The email sent at excerpt request time contains the link to this endpoint.
    """
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.status == JobStatus.PENDING:
        return {"job_id": job_id, "status": "pending", "message": "Still processing. Try again shortly."}
    if job.status == JobStatus.ERROR:
        raise HTTPException(status_code=500, detail=f"Job failed: {job.error}")
    if job.pdf_path is None or not job.pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk.")

    return {
        "job_id": job_id,
        "status": "ready",
        "filename": job.pdf_path.name,
        "message": "Excerpt is ready and saved on the server.",
    }


@router.get("/{job_id}/file")
async def download_file(job_id: str):
    """Download the actual PDF file bytes. Returns 202 if still processing."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.status == JobStatus.PENDING:
        raise HTTPException(status_code=202, detail="Job is still processing. Try again shortly.")
    if job.status == JobStatus.ERROR:
        raise HTTPException(status_code=500, detail=f"Job failed: {job.error}")
    if job.pdf_path is None or not job.pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk.")

    return FileResponse(
        path=str(job.pdf_path),
        media_type="application/pdf",
        filename=job.pdf_path.name,
    )

