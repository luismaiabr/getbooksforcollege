"""Supabase Database integration service."""

import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_client: Client | None = None

def get_db() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def is_book_renamed(file_id: str) -> bool:
    """Check if the book has already been renamed according to Supabase."""
    db = get_db()
    response = db.table("renamed_books").select("has_been_renamed").eq("file_id", file_id).execute()
    data = response.data
    if not data:
        return False
    return data[0].get("has_been_renamed", False)

def mark_book_renamed(file_id: str, original_name: str, new_name: str, categories: list[str], folder: str) -> None:
    """Upsert the book status to Supabase as successfully renamed."""
    db = get_db()
    payload = {
        "file_id": file_id,
        "original_name": original_name,
        "new_name": new_name,
        "categories": categories,
        "folder": folder,
        "has_been_renamed": True
    }
    db.table("renamed_books").upsert(payload).execute()


def update_book_folder(file_id: str, new_folder: str) -> None:
    """Update the folder of a book in Supabase."""
    db = get_db()
    db.table("renamed_books").update({"folder": new_folder}).eq("file_id", file_id).execute()


def get_all_renamed_books() -> dict[str, dict]:
    """Return a dictionary of {file_id: {"new_name": str, "categories": list, "folder": str}} for all renamed books."""
    db = get_db()
    response = db.table("renamed_books").select("file_id, new_name, categories, folder, has_been_renamed").eq("has_been_renamed", True).execute()
    result = {}
    for row in response.data:
        result[row["file_id"]] = {
            "name": row.get("new_name") or "",
            "categories": row.get("categories") or [],
            "folder": row.get("folder") or ""
        }
    return result


def save_excerpt(file_id: str, start_page: int, end_page: int, has_been_studied: bool = False) -> dict:
    """Save a new excerpt record to Supabase and return the created record."""
    db = get_db()
    payload = {
        "google_drive_file_id": file_id,
        "start_page": start_page,
        "end_page": end_page,
        "has_been_studied": has_been_studied
    }
    response = db.table("excerpts").insert(payload).execute()
    if not response.data:
        raise ValueError("Failed to insert excerpt record")
    return response.data[0]


def get_excerpts_by_book(file_id: str) -> list[dict]:
    """Get all excerpts for a specific book."""
    db = get_db()
    response = db.table("excerpts").select("*").eq("google_drive_file_id", file_id).execute()
    return response.data


def update_excerpt_studied_status(excerpt_id: int, has_been_studied: bool) -> dict:
    """Update the studied status of an excerpt."""
    db = get_db()
    response = db.table("excerpts").update({"has_been_studied": has_been_studied}).eq("id", excerpt_id).execute()
    if not response.data:
        raise ValueError(f"Excerpt with id {excerpt_id} not found")
    return response.data[0]
