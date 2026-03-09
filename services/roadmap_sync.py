"""Background job for synchronizing and parsing Teaching Roadmaps using an LLM."""

import asyncio
import json

from services import cache, db, drive, llm, pdf_processor

async def sync_loop():
    """ Runs every 12 hours (or on startup) to check for teaching plans, analyze them, and store them in Supabase. """
    print("Automated Teaching Roadmap Sync Loop started.")
    
    while True:
        try:
            print("[RoadmapSync] Checking for PDFs in PLANOS_DE_ENSINO...")
            folder_id = drive.find_folder_by_path("PLANOS_DE_ENSINO")
            
            if not folder_id:
                print("[RoadmapSync] PLANOS_DE_ENSINO folder not found. Skipping.")
            else:
                plans = drive.list_folder_files(folder_id, prefix="PLANOS_DE_ENSINO")
                
                # Fetch existing teaching roadmaps from DB to check if we already parsed this file
                # Assuming supabase table 'teaching_roadmap'
                supabase = db.get_db()
                # Get unique file_ids already in the DB
                response = supabase.table("teaching_roadmap").select("file_id").execute()
                existing_file_ids = {row["file_id"] for row in response.data}
                
                for plan in plans:
                    file_id = plan["id"]
                    file_name = plan["name"]
                    
                    if file_id in existing_file_ids:
                        print(f"[RoadmapSync] Plan '{file_name}' already synchronized. Skipping.")
                        continue
                        
                    print(f"[RoadmapSync] Processing new teaching plan: '{file_name}'")
                    
                    # Ensure we have the PDF locally, then extract content transiently.
                    local_name = file_name
                    pdf_path = cache.get_pdf_path(local_name)
                    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                        try:
                            drive.download_book(file_id, pdf_path)
                        except Exception as exc:
                            print(f"[RoadmapSync] Download error for {file_name}: {exc}")
                            continue

                    try:
                        loop = asyncio.get_running_loop()
                        pages, _ = await loop.run_in_executor(
                            None,
                            pdf_processor.extract_book_content,
                            pdf_path,
                        )
                    except Exception as exc:
                        print(f"[RoadmapSync] PDF parse error for {file_name}: {exc}")
                        continue

                    # Read all pages of text to send to the LLM
                    # Text from all pages (teaching plans are usually short, 3-10 pages)
                    full_text = "\n\n".join([p["text"] for p in pages])
                    
                    if not full_text.strip():
                        print(f"[RoadmapSync] No text extracted for {file_name}, skipping.")
                        continue
                        
                    print(f"[RoadmapSync] Asking LLM to analyze teaching plan: {file_name}")
                    structured_plan = await analyze_teaching_plan(full_text, file_name, file_id)
                    
                    if not structured_plan or not structured_plan.get("lessons"):
                        print(f"[RoadmapSync] Failed to parse structured data for {file_name}")
                        continue
                        
                    print(f"[RoadmapSync] Found {len(structured_plan['lessons'])} lessons for {file_name}. Saving to Supabase...")
                    
                    for lesson in structured_plan["lessons"]:
                        # Insert into teaching_roadmap
                        payload = {
                            "file_id": lesson["file_id"],
                            "file_name": lesson["file_name"],
                            "course_name": lesson["course_name"],
                            "lesson_title": lesson["lesson_title"],
                            "lesson_description": lesson["lesson_description"],
                            "strategy_for_this_lesson": lesson["strategy_for_this_lesson"],
                            "has_been_studied": False
                        }
                        if lesson.get("date_of_lesson"):
                            payload["date_of_lesson"] = lesson["date_of_lesson"]
                            
                        # Perform UPSERT via API - Supabase SDK natively supports upsert, assuming unique constraint exists
                        try:
                            supabase.table("teaching_roadmap").upsert(payload, on_conflict="file_id, lesson_title, date_of_lesson").execute()
                        except Exception as exc:
                            print(f"[RoadmapSync] DB upsert error for lesson '{lesson['lesson_title']}': {type(exc).__name__}: {exc}")
                            print(f"[RoadmapSync] Payload was: {payload}")
                            
                    print(f"[RoadmapSync] Successfully processed '{file_name}'")
                    
        except Exception as exc:
            print(f"[RoadmapSync] Unexpected error in sync loop: {exc}")
            
        print("[RoadmapSync] Loop finished. Sleeping for 12 hours...")
        await asyncio.sleep(43200) # 12 hours


async def analyze_teaching_plan(text_content: str, file_name: str, file_id: str) -> dict:
    client = llm.get_llm_client()
    
    system_prompt = f"""You are an expert at extracting study roadmaps from university teaching plans (Planos de Ensino).
    Extract all lessons/topics, their descriptions, and dates from the provided text.
    
    For each lesson, generate a 'strategy_for_this_lesson'. 
    The strategy should follow the mindset: 'foco em fazer bem feito e apreciar a experiência'. 
    Suggest deep work, specific study materials, or reflective practices. DO NOT RUSH.
    
    Output MUST be a JSON object matching this schema exactly:
    {{
        "course_name": "Name of the course",
        "lessons": [
            {{
                "lesson_title": "Short title",
                "lesson_description": "Detailed description or objectives",
                "date_of_lesson": "YYYY-MM-DD or null if no exact date is specified",
                "strategy_for_this_lesson": "Deep work strategy...",
                "course_name": "Name of the course",
                "file_name": "{file_name}",
                "file_id": "{file_id}"
            }}
        ]
    }}
    """
    
    user_prompt = f"Here is the text from the teaching plan PDF:\n\n{text_content}"
    
    try:
        response = await client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content
        print(f"[RoadmapSync] LLM raw response for '{file_name}': {raw_content[:300]}...")
        parsed = json.loads(raw_content)
        print(f"[RoadmapSync] Parsed {len(parsed.get('lessons', []))} lessons from LLM response for '{file_name}'")
        return parsed
    except json.JSONDecodeError as e:
        print(f"[RoadmapSync] JSON parse error for {file_name}: {e}. Raw content: {raw_content[:500]}")
        return {}
    except Exception as e:
        print(f"[RoadmapSync] LLM call error for {file_name}: {type(e).__name__}: {e}")
        return {}
