"""Router for GET /books."""

from fastapi import APIRouter, HTTPException

from schemas.whole_book import DriveBook
from services import db, drive

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[DriveBook])
async def list_books():
    """Return all PDF books with id, preferred name, and rename status."""
    try:
        books = drive.list_books()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Drive error: {exc}") from exc

    tracked_books = db.get_tracked_books()
    result = []
    
    for b in books:
        file_id = b["id"]
        # If the file hasn't been renamed by the AI yet, just use the original Drive name
        db_meta = tracked_books.get(file_id, {})
        has_been_renamed = db_meta.get("has_been_renamed", False)
        categories = db_meta.get("categories", [])
        
        # Name is strictly what's on Drive now
        name = b["name"]
        folder = b.get("folder", "")
        
        # Override with DB meta if it's there
        if folder == "" and db_meta and "folder" in db_meta:
            folder = db_meta.get("folder", "")

        is_available = db_meta.get("has_content", False)
        
        result.append(
            DriveBook(
                id=file_id,
                name=name,
                folder=folder,
                has_been_renamed=has_been_renamed,
                categories=categories,
                is_available=is_available,
            )
        )
    return result


@router.get("/folder/{folder_path:path}", response_model=list[DriveBook])
async def list_books_in_folder(folder_path: str):
    """Return all PDF books inside a specific slash-delimited folder path."""
    folder_id = drive.find_folder_by_path(folder_path)
    if not folder_id:
        raise HTTPException(status_code=404, detail=f"Folder '{folder_path}' not found in root.")

    try:
        books = drive.list_folder_files(folder_id, prefix=folder_path.strip("/"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Drive error: {exc}") from exc

    # Reuse the same logic as the main list_books for metadata
    tracked_books = db.get_tracked_books()
    result = []
    
    for b in books:
        file_id = b["id"]
        db_meta = tracked_books.get(file_id, {})
        has_been_renamed = db_meta.get("has_been_renamed", False)
        categories = db_meta.get("categories", [])
        name = b["name"]
        folder = b.get("folder", "")
        
        is_available = db_meta.get("has_content", False)
        
        result.append(
            DriveBook(
                id=file_id,
                name=name,
                folder=folder,
                has_been_renamed=has_been_renamed,
                categories=categories,
                is_available=is_available,
            )
        )
    return result
