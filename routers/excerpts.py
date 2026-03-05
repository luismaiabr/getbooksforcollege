"""Router for excerpt management endpoints."""

from fastapi import APIRouter, HTTPException

from schemas.whole_book import SaveExcerptRequest, ExcerptRecord
from services import db

router = APIRouter(prefix="/excerpts", tags=["excerpts"])


@router.post("", response_model=ExcerptRecord, status_code=201)
async def save_excerpt(request: SaveExcerptRequest):
    """
    Save a new excerpt record to the database.
    
    This endpoint is called after successfully requesting an excerpt
    to track what has been requested and whether it has been studied.
    
    Validates:
    - book_id exists in renamed_books table
    - start_page <= end_page
    - pages are positive numbers
    """
    # Validation: Check if book exists
    if not db.is_book_renamed(request.book_id):
        raise HTTPException(
            status_code=404,
            detail=f"Book with id '{request.book_id}' not found in renamed_books"
        )
    
    # Validation: Check page ranges
    if request.start_page <= 0 or request.end_page <= 0:
        raise HTTPException(
            status_code=400,
            detail="Page numbers must be positive integers"
        )
    
    if request.start_page > request.end_page:
        raise HTTPException(
            status_code=400,
            detail=f"start_page ({request.start_page}) cannot be greater than end_page ({request.end_page})"
        )
    
    # Save to database
    try:
        record = db.save_excerpt(
            file_id=request.book_id,
            start_page=request.start_page,
            end_page=request.end_page,
            has_been_studied=request.has_been_studied
        )
        return ExcerptRecord(**record)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc


@router.get("/{book_id}", response_model=list[ExcerptRecord])
async def get_excerpts_for_book(book_id: str):
    """Get all excerpts for a specific book."""
    try:
        records = db.get_excerpts_by_book(book_id)
        return [ExcerptRecord(**r) for r in records]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc


@router.patch("/{excerpt_id}/studied", response_model=ExcerptRecord)
async def update_studied_status(excerpt_id: int, has_been_studied: bool):
    """Update the studied status of an excerpt."""
    try:
        record = db.update_excerpt_studied_status(excerpt_id, has_been_studied)
        return ExcerptRecord(**record)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
