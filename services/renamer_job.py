"""Background job for automated book renaming using LLM."""

import asyncio

from services import cache, db, drive, llm, pdf_processor


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
                
                # Fetch text content directly from the PDF and persist it with the rename record.
                local_name = original_drive_name
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
                    pages, ocr_used = await loop.run_in_executor(
                        None,
                        pdf_processor.extract_book_content,
                        pdf_path,
                    )
                except Exception as exc:
                    print(f"[Renamer] PDF parse error for {original_drive_name}: {exc}")
                    continue

                ocr_status = "yes" if ocr_used else "not_necessary"

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
                    db.mark_book_renamed(
                        file_id,
                        original_drive_name,
                        new_name,
                        categories,
                        folder_name,
                        content=pages,
                        ocr_has_been_applyed=ocr_status,
                    )
                    print(f"[Renamer] Successfully renamed and tracked '{original_drive_name}' -> '{new_name}' in folder '{folder_name}' (ocr={ocr_status})")
                except Exception as exc:
                    print(f"[Renamer] Failed to save status to Supabase: {exc}")

            # ── Re-OCR pass: fix books already in DB that still have ocr_has_been_applyed='no' ──
            print("[Renamer] Checking for existing books that need OCR re-processing...")
            try:
                books_needing_ocr = db.get_books_needing_ocr()
            except Exception as exc:
                print(f"[Renamer] Could not fetch books needing OCR: {exc}")
                books_needing_ocr = []

            for book_row in books_needing_ocr:
                file_id = book_row["file_id"]
                # Content is considered empty when every page has no text
                existing_content = book_row.get("content") or []
                total_chars = sum(len(p.get("text", "")) for p in existing_content)
                if total_chars > 0:
                    # Content looks fine — just update the status without re-downloading
                    try:
                        db.update_book_ocr_status(file_id, existing_content, "not_necessary")
                    except Exception as exc:
                        print(f"[Renamer] OCR pass: failed to update status for {file_id}: {exc}")
                    continue

                # Content is empty — need to re-download and OCR
                drive_name = book_row.get("new_name") or book_row.get("original_name") or file_id
                folder_name = book_row.get("folder", "")
                pdf_path = cache.get_pdf_path(drive_name)
                if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                    try:
                        drive.download_book(file_id, pdf_path)
                    except Exception as exc:
                        print(f"[Renamer] OCR pass: download error for '{drive_name}': {exc}")
                        continue

                try:
                    loop = asyncio.get_running_loop()
                    pages, ocr_used = await loop.run_in_executor(
                        None,
                        pdf_processor.extract_book_content,
                        pdf_path,
                    )
                except Exception as exc:
                    print(f"[Renamer] OCR pass: PDF parse error for '{drive_name}': {exc}")
                    continue

                ocr_status = "yes" if ocr_used else "not_necessary"
                try:
                    db.update_book_ocr_status(file_id, pages, ocr_status)
                    print(f"[Renamer] OCR pass: updated '{drive_name}' with ocr={ocr_status}")
                except Exception as exc:
                    print(f"[Renamer] OCR pass: failed to save to Supabase for '{drive_name}': {exc}")

        except Exception as exc:
            print(f"[Renamer] Unexpected error in renaming loop: {exc}")
            
        print("[Renamer] Loop finished. Sleeping for 30 minutes...")
        await asyncio.sleep(1800)
