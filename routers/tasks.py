from typing import List, Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, HTTPException, Query, status
from schemas.tasks import Task, TaskCreate, TaskPriority, TaskStatus
from services import db_tasks

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate):
    """Create a new task."""
    try:
        return db_tasks.create_task(task)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[Task])
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

@router.patch("/{task_id}", response_model=Task)
async def update_task(task_id: UUID, updates: dict):
    """Update task fields."""
    try:
        task = db_tasks.update_task(task_id, updates)
        return task
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
