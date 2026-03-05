import httpx
from uuid import UUID
from datetime import date
import asyncio

# Assuming the server is running or we use TestClient. 
# For now, let's use TestClient internally if possible, or expect it to be running.
# Since I can't easily start a background process and wait for it to be ready in one go without potential issues,
# I will use FastAPI's TestClient.

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_crud_lifecycle():
    # 1. Create a task
    task_payload = {
        "title": "Test Task",
        "category": "Testing",
        "priority": "HIGH",
        "status": "PENDING",
        "repeat": "never",
        "strategy": "This is a test strategy",
        "target_date": str(date.today()),
        "metadata": {"test": True}
    }
    
    response = client.post("/tasks/", json=task_payload)
    assert response.status_code == 201
    task = response.json()
    task_id = task["id"]
    assert task["title"] == "Test Task"
    
    # 2. Get the task
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["id"] == task_id
    
    # 3. List tasks
    response = client.get("/tasks/", params={"category": "Testing"})
    assert response.status_code == 200
    tasks = response.json()
    assert any(t["id"] == task_id for t in tasks)
    
    # 4. Update the task
    update_payload = {"status": "DONE", "strategy": "Updated strategy"}
    response = client.patch(f"/tasks/{task_id}", json=update_payload)
    assert response.status_code == 200
    updated_task = response.json()
    assert updated_task["status"] == "DONE"
    assert updated_task["strategy"] == "Updated strategy"
    
    # 5. Delete the task
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204
    
    # 6. Verify deletion
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 404
    print("CRUD Lifecycle test passed!")

if __name__ == "__main__":
    try:
        test_crud_lifecycle()
        print("All tests passed successfully.")
    except Exception as e:
        print(f"Tests failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
