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


def mark_book_renamed(file_id: str, original_name: str, new_name: str, categories: list[str]) -> None:
    """Upsert the book status to Supabase as successfully renamed."""
    db = get_db()
    payload = {
        "file_id": file_id,
        "original_name": original_name,
        "new_name": new_name,
        "categories": categories,
        "has_been_renamed": True
    }
    db.table("renamed_books").upsert(payload).execute()


def get_all_renamed_books() -> dict[str, dict]:
    """Return a dictionary of {file_id: {"new_name": str, "categories": list}} for all renamed books."""
    db = get_db()
    response = db.table("renamed_books").select("file_id, new_name, categories, has_been_renamed").eq("has_been_renamed", True).execute()
    result = {}
    for row in response.data:
        result[row["file_id"]] = {
            "name": row.get("new_name") or "",
            "categories": row.get("categories") or []
        }
    return result
