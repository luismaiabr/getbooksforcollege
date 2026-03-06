"""Background job for automated book renaming using LLM."""

import asyncio
import json
from services import drive, db, cache, llm, pdf_processor


async def renaming_loop():
    """ Runs every 30 minutes to check for unrenamed books, analyze them, and rename them. """
    print("Automated Renaming Loop started.")
    
    while True:
        try:
            print("[Renamer] Checking for completely unrenamed books...")
            books = drive.list_books()
            # Fetch all renamed books once per iteration to compare folders
            renamed_books_map = db.get_all_renamed_books()
            
            for b in books:
                file_id = b["id"]
                original_drive_name = b["name"]
                folder_name = b.get("folder", "")
                
                # Check Supabase to see if we already renamed this file
                if file_id in renamed_books_map:
                    db_folder = renamed_books_map[file_id].get("folder", "")
                    if db_folder != folder_name:
                        print(f"[Renamer] Updating folder for '{original_drive_name}' from '{db_folder}' to '{folder_name}'")
                        db.update_book_folder(file_id, folder_name)
                    continue
                
                # Fetch text content (it should be pre-computed by the main lifespan task)
                # We use the current name in drive to find the local files.
                local_name = original_drive_name
                content_path = cache.get_content_path(local_name)
                
                if not (content_path.exists() and content_path.stat().st_size > 0):
                    # Text content is missing... wait for the pre-computation task or do it here
                    pdf_path = cache.get_pdf_path(local_name)
                    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                        try:
                            drive.download_book(file_id, pdf_path)
                        except FileNotFoundError:
                            print(f"[Renamer] Book '{original_drive_name}' was deleted from Drive — skipping.")
                            continue
                        except Exception as exc:
                            print(f"[Renamer] Drive download error for {original_drive_name}: {exc}")
                            continue
                    try:
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(
                            None, 
                            pdf_processor.build_content_json, 
                            local_name, pdf_path, content_path
                        )
                    except Exception as exc:
                        print(f"[Renamer] PDF parse error for {original_drive_name}: {exc}")
                        continue
                
                # Read the first few pages of text
                data = json.loads(content_path.read_text(encoding="utf-8"))
                pages = data.get("pages", [])
                first_pages_text = "\n\n".join([p["text"] for p in pages[:4]])
                
                if not first_pages_text.strip():
                    print(f"[Renamer] No text extracted for {original_drive_name}, skipping.")
                    continue
                
                print(f"[Renamer] Asking LLM to analyze: {original_drive_name}")
                result = await llm.analyze_book_cover(first_pages_text)
                new_name = result["name"].replace("/", "-").replace("\\", "-") # basic sanitization
                categories = result["categories"]
                
                print(f"[Renamer] LLM decided on new name: {new_name}")
                
                # Rename the file in Google Drive
                try:
                    drive.rename_file(file_id, new_name)
                except Exception as exc:
                    print(f"[Renamer] Failed to rename on Drive: {exc}")
                    continue
                
                # Rename the local directory so we don't redownload it
                try:
                    cache.rename_book(local_name, new_name)
                except FileExistsError:
                    print(f"[Renamer] Local directory {new_name} already exists. Might be a duplicate.")
                
                # Save to Supabase
                try:
                    db.mark_book_renamed(file_id, original_drive_name, new_name, categories, folder_name)
                    print(f"[Renamer] Successfully renamed and tracked '{original_drive_name}' -> '{new_name}' in folder '{folder_name}'")
                except Exception as exc:
                    print(f"[Renamer] Failed to save status to Supabase: {exc}")
                    
        except Exception as exc:
            print(f"[Renamer] Unexpected error in renaming loop: {exc}")
            
        print("[Renamer] Loop finished. Sleeping for 30 minutes...")
        await asyncio.sleep(1800)
