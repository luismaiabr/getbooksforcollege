from typing import List, Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, HTTPException, Query, status
from schemas.tasks import Task, TaskCreate, TaskPriority, TaskStatus, TaskWithEntry
from services import db_tasks

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate):
    """Create a new task."""
    try:
        return db_tasks.create_task(task)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[TaskWithEntry])
async def list_tasks(
    category: Optional[str] = Query(None),
    status: Optional[TaskStatus] = Query(None),
    target_date: Optional[date] = Query(None)
):
    """List tasks with optional filters."""
    return db_tasks.get_all_tasks(category, status, target_date)

@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: UUID):
    """Get task details."""
    task = db_tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/{task_id}", response_model=TaskWithEntry)
async def update_task(
    task_id: UUID, 
    updates: dict, 
    target_date: Optional[date] = Query(None)
):
    """Update task fields."""
    try:
        # Special logic: If status is provided, we use the specialized update_task_status
        if "status" in updates:
            new_status = TaskStatus(updates.pop("status"))
            # update_task_status handles the redirection logic internally (Template vs Instance)
            db_tasks.update_task_status(task_id, new_status, target_date)
            
        # Perform other updates if any
        if updates:
            db_tasks.update_task(task_id, updates)
            
        # Return the merged view for the requested date
        results = db_tasks.get_all_tasks(target_date=target_date or date.today())
        for r in results:
            if r.id == task_id:
                return r
        
        # If not found in filtered list, get base task
        base = db_tasks.get_task(task_id)
        return TaskWithEntry(**base.model_dump())
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID):
    """Delete a task."""
    success = db_tasks.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return None
