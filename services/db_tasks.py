from uuid import UUID
from datetime import date
from typing import Optional, List, Dict, Any
from .db import get_db
from schemas.tasks import Task, TaskCreate, TaskWithEntry, TaskEntry, TaskStatus, TaskRepeatInterval

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
    
    new_task = Task.model_validate(response.data[0])
    
    # If it's a repeating task, generate the first entry for today immediately
    if new_task.repeat != TaskRepeatInterval.NEVER:
        entry_payload = {
            "task_id": str(new_task.id),
            "target_date": date.today().isoformat(),
            "status": TaskStatus.PENDING
        }
        db.table("task_entries").insert(entry_payload).execute()
        
    return new_task

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
) -> List[TaskWithEntry]:
    """
    Retrieve all tasks with optional filtering.
    If target_date is provided, merges habit templates with their daily status from task_entries.
    """
    db = get_db()
    
    # 1. Get all base tasks
    query = db.table("tasks").select("*")
    if category:
        query = query.eq("category", category)
    if status and not target_date:
        # If target_date is not provided, we filter on the base task status (for one-offs)
        query = query.eq("status", status)
        
    tasks_res = query.order("created_at", desc=True).execute()
    tasks_list = [Task.model_validate(row) for row in tasks_res.data]
    
    if not target_date:
        # Simple view
        return [TaskWithEntry(**t.model_dump()) for t in tasks_list]

    # 2. Get entries for the specific date
    date_str = target_date.isoformat()
    entries_res = db.table("task_entries").select("*").eq("target_date", date_str).execute()
    entries_map = {row["task_id"]: row for row in entries_res.data}
    
    # 3. Merge
    results = []
    for t in tasks_list:
        tid = str(t.id)
        entry = entries_map.get(tid)
        
        # Determine status for the response
        # Priority: TaskEntry status > Template status (if never repeat) > DEFAULT PENDING
        effective_status = t.status
        if t.repeat != TaskRepeatInterval.NEVER:
            effective_status = entry["status"] if entry else TaskStatus.PENDING
            
        # If filter on status was requested, check it here for merged results
        if status and effective_status != status:
            continue
            
        with_entry = TaskWithEntry(
            **t.model_dump(),
            entry_id=UUID(entry["id"]) if entry else None,
            entry_status=entry["status"] if entry else None
        )
        # Override the top-level status for the UI to see the "daily" status
        with_entry.status = effective_status
        results.append(with_entry)
        
    return results

def update_task_status(task_id: UUID, new_status: TaskStatus, target_date: Optional[date] = None) -> Any:
    """
    Update task status.
    If task is recurring, updates/inserts into task_entries for target_date.
    """
    db = get_db()
    task = get_task(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")
        
    if task.repeat == TaskRepeatInterval.NEVER:
        # One-off task: update base table
        response = db.table("tasks").update({"status": new_status}).eq("id", str(task_id)).execute()
        return Task.model_validate(response.data[0])
    else:
        # Repeating task: update entries table
        effective_date = target_date or date.today()
        payload = {
            "task_id": str(task_id),
            "target_date": effective_date.isoformat(),
            "status": new_status
        }
        # Upsert logic
        response = db.table("task_entries").upsert(payload, on_conflict="task_id,target_date").execute()
        return response.data[0]

def update_task(task_id: UUID, update_data: Dict[str, Any]) -> Task:
    """Update an existing task template."""
    db = get_db()
    tid = str(task_id)
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
    return len(response.data) > 0
