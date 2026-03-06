"""Router for Teaching Roadmap endpoints (MCP tool handlers)."""

from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from services import db

router = APIRouter(prefix="/roadmap", tags=["roadmap"])

class StudiedUpdate(BaseModel):
    has_been_studied: bool

@router.get("")
async def get_teaching_roadmaps(course_name: Optional[str] = None):
    """Retrieve tracking info for all lessons in the Teaching Roadmap."""
    supabase = db.get_db()
    query = supabase.table("teaching_roadmap").select("*")
    
    if course_name:
        query = query.eq("course_name", course_name)
        
    try:
        res = query.order("date_of_lesson").execute()
        return res.data
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Database error: {exc}")


@router.post("/{lesson_id}/studied")
async def mark_lesson_studied(lesson_id: str, update: StudiedUpdate):
    """Mark a specific lesson as studied or not studied in the teaching roadmap."""
    supabase = db.get_db()
    try:
        res = supabase.table("teaching_roadmap").update({
            "has_been_studied": update.has_been_studied
        }).eq("id", lesson_id).execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Lesson not found.")
            
        return res.data[0]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Database error: {exc}")
