"""
routers/tasks.py
GET    /tasks?tenantId=xxx
GET    /tasks/:id
POST   /tasks
PUT    /tasks/:id
DELETE /tasks/:id
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _row_to_task(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "title": row[2], "description": row[3] or "",
        "dueDate": str(row[4]) if row[4] else "",
        "priority": row[5], "status": row[6],
        "assignedTo": row[7] or "", "relatedTo": row[8] or "",
        "createdBy": row[9] or "", "createdAt": str(row[10]), "updatedAt": str(row[11]),
    }


class TaskBody(BaseModel):
    tenantId: str
    title: str
    description: Optional[str] = ""
    dueDate: Optional[str] = None
    priority: Optional[str] = "medium"
    status: Optional[str] = "open"
    assignedTo: Optional[str] = None
    relatedTo: Optional[str] = ""
    createdBy: Optional[str] = None


@router.get("")
def get_tasks(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, title, description, due_date, priority, status, assigned_to, related_to, created_by, created_at, updated_at "
                "FROM tasks WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
    return [_row_to_task(r) for r in rows]


@router.get("/{task_id}")
def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, title, description, due_date, priority, status, assigned_to, related_to, created_by, created_at, updated_at "
                "FROM tasks WHERE id = %s",
                (task_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return _row_to_task(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(body: TaskBody, current_user: dict = Depends(get_current_user)):
    created_by = body.createdBy or current_user["id"]
    assigned_to = body.assignedTo or None
    related_to = body.relatedTo or None
    due_date = body.dueDate or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (tenant_id, title, description, due_date, priority, status, assigned_to, related_to, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING id, tenant_id, title, description, due_date, priority, status, assigned_to, related_to, created_by, created_at, updated_at",
                (body.tenantId, body.title, body.description, due_date, body.priority,
                 body.status, assigned_to, related_to, created_by)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_task(row)


@router.put("/{task_id}")
def update_task(task_id: str, body: TaskBody, current_user: dict = Depends(get_current_user)):
    assigned_to = body.assignedTo or None
    related_to = body.relatedTo or None
    due_date = body.dueDate or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET title=%s, description=%s, due_date=%s, priority=%s, status=%s, assigned_to=%s, related_to=%s, updated_at=NOW() "
                "WHERE id=%s "
                "RETURNING id, tenant_id, title, description, due_date, priority, status, assigned_to, related_to, created_by, created_at, updated_at",
                (body.title, body.description, due_date, body.priority, body.status,
                 assigned_to, related_to, task_id)
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return _row_to_task(row)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit()
    return None
