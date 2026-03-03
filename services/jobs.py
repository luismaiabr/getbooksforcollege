"""In-memory job store for background excerpt generation."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class JobStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    ERROR = "error"


@dataclass
class Job:
    job_id: str
    status: JobStatus = JobStatus.PENDING
    pdf_path: Path | None = None
    error: str | None = None


# Simple in-process store — keyed by job_id (book name)
_store: dict[str, Job] = {}


def create_or_reset(job_id: str) -> Job:
    job = Job(job_id=job_id)
    _store[job_id] = job
    return job


def get(job_id: str) -> Job | None:
    return _store.get(job_id)


def set_ready(job_id: str, pdf_path: Path) -> None:
    if job_id in _store:
        _store[job_id].status = JobStatus.READY
        _store[job_id].pdf_path = pdf_path


def set_error(job_id: str, error: str) -> None:
    if job_id in _store:
        _store[job_id].status = JobStatus.ERROR
        _store[job_id].error = error
