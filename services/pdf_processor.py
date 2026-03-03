"""PDF text extraction and page-slicing utilities."""

import io
import json
from pathlib import Path

import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter

from schemas.whole_book import PageContent


def extract_text(pdf_path: Path) -> list[PageContent]:
    """Extract text from every page of a PDF using PyMuPDF."""
    doc = fitz.open(str(pdf_path))
    pages: list[PageContent] = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        pages.append(PageContent(page=i, text=text))
    doc.close()
    return pages


def build_content_json(book_name: str, pdf_path: Path, content_path: Path) -> list[PageContent]:
    """Extract text from PDF, write content.json, and return the pages list."""
    pages = extract_text(pdf_path)
    data = {"pages": [p.model_dump() for p in pages]}
    content_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return pages


def slice_pdf(pdf_path: Path, start: int, end: int) -> io.BytesIO:
    """
    Return a BytesIO containing a PDF with pages [start, end] (1-indexed, inclusive).
    Raises ValueError if range is invalid.
    """
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)

    if start < 1 or end < start or end > total:
        raise ValueError(
            f"Invalid page range [{start}, {end}] for a {total}-page PDF."
        )

    writer = PdfWriter()
    for page_num in range(start - 1, end):  # pypdf is 0-indexed
        writer.add_page(reader.pages[page_num])

    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer
