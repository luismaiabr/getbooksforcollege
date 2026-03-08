"""PDF text extraction and page-slicing utilities."""

import io
from pathlib import Path

import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter

from schemas.whole_book import PageContent

# If average extracted words per page falls below this threshold,
# the PDF is treated as a scanned image and OCR is applied.
_OCR_WORDS_THRESHOLD = 20


def apply_ocr_to_pdf(pdf_path: Path) -> list[PageContent]:
    """Convert PDF pages to images and extract text via Tesseract OCR."""
    from pdf2image import convert_from_path  # deferred – only needed for scanned PDFs
    import pytesseract

    images = convert_from_path(str(pdf_path))
    pages: list[PageContent] = []
    for i, image in enumerate(images, start=1):
        text = pytesseract.image_to_string(image)
        text = text.replace("\x00", "")  # Postgres does not support null bytes
        pages.append(PageContent(page=i, text=text))
    return pages


def extract_text(pdf_path: Path) -> tuple[list[PageContent], bool]:
    """Extract text from every page of a PDF.

    Attempts standard PyMuPDF extraction first.  If the average words per
    page is below *_OCR_WORDS_THRESHOLD*, falls back to Tesseract OCR.

    Returns:
        A tuple of (pages, ocr_was_used).
    """
    doc = fitz.open(str(pdf_path))
    pages: list[PageContent] = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        text = text.replace("\x00", "")  # Postgres does not support null bytes
        pages.append(PageContent(page=i, text=text))
    doc.close()

    if pages:
        avg_words = sum(len(p.text.split()) for p in pages) / len(pages)
        print(f"[PDF Processor] Extracted an average of {avg_words:.2f} words per page.")
        if avg_words < _OCR_WORDS_THRESHOLD:
            print(f"[PDF Processor] Average {avg_words:.2f} is below the threshold of {_OCR_WORDS_THRESHOLD}. Applying OCR...")
            return apply_ocr_to_pdf(pdf_path), True

    return pages, False


def extract_book_content(pdf_path: Path) -> tuple[list[dict], bool]:
    """Extract text from PDF and return (JSON-serializable page list, ocr_used)."""
    pages, ocr_used = extract_text(pdf_path)
    return [page.model_dump() for page in pages], ocr_used


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
