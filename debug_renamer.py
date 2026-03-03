import asyncio
from services import drive, llm
import json
from pathlib import Path

async def main():
    books = drive.list_books()
    book = next((b for b in books if b["name"] == "LOGICA PARTE 1"), None)
    if not book:
        print("Book not found in Drive")
        return
        
    print(f"File ID: {book['id']}")
    content_path = Path(f"../temp/complete_books/{book['name']}/content.json").resolve()
    print(f"Reading from {content_path} - Exists: {content_path.exists()}")
    if not content_path.exists():
        print("Content path not found")
        return
        
    data = json.loads(content_path.read_text(encoding="utf-8"))
    pages = data.get("pages", [])
    first_pages_text = "\n\n".join([p["text"] for p in pages[:4]])
    
    if not first_pages_text.strip():
        print("No text extracted for LOGICA PARTE 1, skipping.")
        return
        
    print(f"Calling LLM for LOGICA PARTE 1. Text length: {len(first_pages_text)}")
    try:
        result = await llm.analyze_book_cover(first_pages_text)
        print(f"LLM Result: {result}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
