from datetime import date, datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

class TaskPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    NOT_FINISHED = "NOT_FINISHED"
    CANCELLED = "CANCELLED"
    POSTPONED = "POSTPONED"

class TaskRepeatInterval(str, Enum):
    NEVER = "never"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIMONTHLY = "bimonthly"
    MONTHLY = "monthly"

class TaskBase(BaseModel):
    title: str
    category: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    repeat: TaskRepeatInterval = TaskRepeatInterval.NEVER
    strategy: Optional[str] = None
    target_date: Optional[date] = Field(default_factory=date.today)
    time_estimate_minutes: Optional[int] = None
    external_link: Optional[str] = None
    parent_task_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
