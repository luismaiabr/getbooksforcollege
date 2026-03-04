"""Manages the temp/complete_books/ cache directory."""

import json
import os
from pathlib import Path

# Allow overriding the cache location via env var (used in Docker).
# Falls back to the original path (../../temp/complete_books) for local dev.
_env_cache = os.getenv("BOOKS_CACHE_DIR")
BASE = Path(_env_cache) if _env_cache else Path(__file__).resolve().parents[2] / "temp" / "complete_books"


# ── Path helpers ──────────────────────────────────────────────────────────────

def get_book_dir(book_name: str) -> Path:
    book_dir = BASE / book_name
    book_dir.mkdir(parents=True, exist_ok=True)
    return book_dir


def get_pdf_path(book_name: str) -> Path:
    return get_book_dir(book_name) / f"{book_name}.pdf"


def get_content_path(book_name: str) -> Path:
    return get_book_dir(book_name) / "content.json"


def get_excerpt_path(book_name: str, start: int, end: int) -> Path:
    excerpts_dir = get_book_dir(book_name) / "excerpts"
    excerpts_dir.mkdir(parents=True, exist_ok=True)
    return excerpts_dir / f"{start}-{end}.pdf"


# ── Rename ────────────────────────────────────────────────────────────────────

def rename_book(old_name: str, new_name: str) -> bool:
    """
    Rename the book's cache folder from old_name to new_name.
    Returns True if renamed, False if the folder didn't exist (silent skip).
    Raises FileExistsError if the new folder already exists.
    """
    old_dir = BASE / old_name
    new_dir = BASE / new_name

    if not old_dir.exists():
        return False

    if new_dir.exists():
        raise FileExistsError(f"A folder named '{new_name}' already exists.")

    old_pdf = old_dir / f"{old_name}.pdf"
    if old_pdf.exists():
        old_pdf.rename(old_dir / f"{new_name}.pdf")

    old_dir.rename(new_dir)
    return True
