from uuid import UUID
from datetime import date
from typing import Optional, List, Dict, Any
from .db import get_db
from schemas.tasks import Task, TaskCreate

def create_task(task_data: TaskCreate) -> Task:
    """Create a new task in Supabase."""
    db = get_db()
    # Pydantic model to dict, handling date and enum conversion
    payload = task_data.model_dump()
    if isinstance(payload.get("target_date"), date):
        payload["target_date"] = payload["target_date"].isoformat()
    
    # Enums are already strings in TaskCreate (str, Enum)
    
    response = db.table("tasks").insert(payload).execute()
    if not response.data:
        raise ValueError("Failed to create task")
    return Task.model_validate(response.data[0])

def get_task(task_id: UUID) -> Optional[Task]:
    """Retrieve a specific task by ID."""
    db = get_db()
    response = db.table("tasks").select("*").eq("id", str(task_id)).execute()
    if not response.data:
        return None
    return Task.model_validate(response.data[0])

def get_all_tasks(
    category: Optional[str] = None, 
    status: Optional[str] = None,
    target_date: Optional[date] = None
) -> List[Task]:
    """Retrieve all tasks with optional filtering."""
    db = get_db()
    query = db.table("tasks").select("*")
    
    if category:
        query = query.eq("category", category)
    if status:
        query = query.eq("status", status)
    if target_date:
        query = query.eq("target_date", target_date.isoformat())
    
    response = query.order("created_at", desc=True).execute()
    return [Task.model_validate(row) for row in response.data]

def update_task(task_id: UUID, update_data: Dict[str, Any]) -> Task:
    """Update an existing task."""
    db = get_db()
    # sanitize task_id
    tid = str(task_id)
    
    # Handle date conversion if present
    if "target_date" in update_data and isinstance(update_data["target_date"], date):
        update_data["target_date"] = update_data["target_date"].isoformat()
    
    response = db.table("tasks").update(update_data).eq("id", tid).execute()
    if not response.data:
        raise ValueError(f"Task with id {task_id} not found or update failed")
    return Task.model_validate(response.data[0])

def delete_task(task_id: UUID) -> bool:
    """Delete a task."""
    db = get_db()
    response = db.table("tasks").delete().eq("id", str(task_id)).execute()
    # Supabase execute() returns data even for deletes if successful
    return len(response.data) > 0
