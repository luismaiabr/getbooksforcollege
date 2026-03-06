import asyncio
from datetime import date, timedelta, datetime
from typing import Dict
from .db_tasks import get_all_tasks, update_task_status, get_db
from schemas.tasks import TaskRepeatInterval, TaskStatus

# Mapping interval to days for due_date calculation: due_date = target_date + interval
INTERVAL_MAP = {
    TaskRepeatInterval.DAILY: 1,
    TaskRepeatInterval.WEEKLY: 7,
    TaskRepeatInterval.BIMONTHLY: 15,
    TaskRepeatInterval.MONTHLY: 30,
}

async def repeated_task_generation_service():
    """
    Background service that ensures habit instances exist for today.
    """
    print("[Background] Starting repeated_task_generation_service")
    while True:
        try:
            today = date.today()
            # Fetch all tasks (templates)
            # We use a direct DB call to avoid our merged logic for this maintenance task
            db = get_db()
            response = db.table("tasks").select("*").neq("repeat", "never").execute()
            
            count = 0
            for row in response.data:
                task_id = row["id"]
                # Create PENDING entry for today if it doesn't exist
                payload = {
                    "task_id": task_id,
                    "target_date": today.isoformat(),
                    "status": "PENDING"
                }
                # Use upsert with no change to status if it already exists? 
                # Actually, our db_tasks handle this via upsert
                # But we only want to "generate" if it doesn't exist to not overwrite a 'DONE' status
                # So we check first
                exists = db.table("task_entries").select("id").eq("task_id", task_id).eq("target_date", today.isoformat()).execute()
                if not exists.data:
                    db.table("task_entries").insert(payload).execute()
                    count += 1
            
            if count > 0:
                print(f"[Background] Generated {count} habit entries for {today}")
            
            # Run once every hour
            await asyncio.sleep(3600) 
        except Exception as e:
            print(f"Error in repeated_task_generation_service: {e}")
            await asyncio.sleep(60)

async def check_repeating_tasks():
    """
    Background service that marks tasks as NOT_FINISHED if they go past due date.
    due_date = target_date + interval
    """
    print("[Background] Starting check_repeating_tasks")
    while True:
        try:
            today = date.today()
            db = get_db()
            
            # 1. Fetch all pending entries
            response = db.table("task_entries").select("*, tasks(repeat)").eq("status", "PENDING").execute()
            
            for entry in response.data:
                target_date_obj = date.fromisoformat(entry["target_date"])
                repeat_interval = entry["tasks"]["repeat"]
                
                days_to_add = INTERVAL_MAP.get(repeat_interval, 1)
                due_date = target_date_obj + timedelta(days=days_to_add)
                
                if due_date < today:
                    # Past due!
                    db.table("task_entries").update({"status": "NOT_FINISHED"}).eq("id", entry["id"]).execute()
            
            # Also check base tasks for one-offs (target_date < today and repeat == 'never' and status == 'PENDING')
            one_offs = db.table("tasks").select("id, target_date").eq("repeat", "never").eq("status", "PENDING").execute()
            for task in one_offs.data:
                if task["target_date"]:
                    t_date = date.fromisoformat(task["target_date"])
                    if t_date < today:
                        db.table("tasks").update({"status": "NOT_FINISHED"}).eq("id", task["id"]).execute()

            # Run once every hour
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"Error in check_repeating_tasks: {e}")
            await asyncio.sleep(60)
