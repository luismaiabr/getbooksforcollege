"""Background job for pre-computing text content of books."""

import asyncio
from services import drive, cache, pdf_processor

async def content_extraction_loop():
    """
    Periodically checks Google Drive for all books and ensures their text 
    is extracted and cached locally in content.json.
    """
    print("Content Extraction Loop started.")
    
    while True:
        try:
            print("[Preprocessor] Checking for missing content.json for all books...")
            try:
                drive_books = drive.list_books()
            except Exception as exc:
                print(f"[Preprocessor] Drive list error: {exc}")
                await asyncio.sleep(60)
                continue

            for b in drive_books:
                book_name = b["name"]
                pdf_path = cache.get_pdf_path(book_name)
                content_path = cache.get_content_path(book_name)

                # Only process if content.json is missing or empty
                if not (content_path.exists() and content_path.stat().st_size > 0):
                    print(f"[Preprocessor] Pre-computing missing content for: {book_name}")
                    
                    # Ensure PDF exists locally first
                    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                        try:
                            drive.download_book(b["id"], pdf_path)
                        except FileNotFoundError:
                            print(f"[Preprocessor] Book '{book_name}' was deleted from Drive — skipping.")
                            continue
                        except Exception as exc:
                            print(f"[Preprocessor] Failed to download {book_name}: {exc}")
                            continue
                            
                    try:
                        # BUILD CONTENT - using run_in_executor because pdf parsing is blocking
                        loop = asyncio.get_running_loop()
                        pages = await loop.run_in_executor(
                            None, 
                            pdf_processor.build_content_json, 
                            book_name, pdf_path, content_path
                        )
                        
                        # LOG STATUS
                        total_char = sum(len(p.text) for p in pages)
                        if total_char == 0:
                            print(f"[Preprocessor] Warning: {book_name} extracted 0 characters. (Possibly scanned PDF)")
                        else:
                            print(f"[Preprocessor] Successfully processed {book_name} ({len(pages)} pages)")
                            
                    except Exception as exc:
                        print(f"[Preprocessor] Failed to parse {book_name}: {exc}")
                        
        except Exception as exc:
            print(f"[Preprocessor] Unexpected error in extraction loop: {exc}")
            
        print("[Preprocessor] Extraction cycle finished. Sleeping for 1 hour...")
        await asyncio.sleep(3600)  # Extract text for all books once every hour
