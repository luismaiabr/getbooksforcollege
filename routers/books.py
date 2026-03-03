"""Router for GET /books."""

from fastapi import APIRouter, HTTPException

from schemas.whole_book import DriveBook
from services import cache, drive, db

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[DriveBook])
async def list_books():
    """Return all PDF books with id, preferred name, and rename status."""
    try:
        books = drive.list_books()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Drive error: {exc}") from exc

    renamed_books = db.get_all_renamed_books()
    result = []
    
    for b in books:
        file_id = b["id"]
        # If the file hasn't been renamed by the AI yet, just use the original Drive name
        db_meta = renamed_books.get(file_id, {})
        has_been_renamed = file_id in renamed_books
        categories = db_meta.get("categories", [])
        
        # Name is strictly what's on Drive now
        name = b["name"]

        content_path = cache.get_content_path(name)
        is_available = content_path.exists() and content_path.stat().st_size > 0
        
        result.append(
            DriveBook(
                id=file_id,
                name=name,
                has_been_renamed=has_been_renamed,
                categories=categories,
                is_available=is_available,
            )
        )
    return result
