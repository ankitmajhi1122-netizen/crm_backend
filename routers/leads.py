"""
routers/leads.py
GET    /leads?tenantId=xxx
GET    /leads/:id
POST   /leads
PUT    /leads/:id
DELETE /leads/:id
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _row_to_lead(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "name": row[2],
        "email": row[3], "phone": row[4], "company": row[5],
        "status": row[6], "source": row[7], "score": row[8],
        "createdBy": row[9] or "", "createdAt": str(row[10]), "updatedAt": str(row[11]),
    }


class LeadBody(BaseModel):
    tenantId: str
    name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    company: Optional[str] = ""
    status: Optional[str] = "new"
    source: Optional[str] = "other"
    score: Optional[int] = 0
    createdBy: Optional[str] = None


@router.get("")
def get_leads(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, email, phone, company, status, source, score, created_by, created_at, updated_at "
                "FROM leads WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
    return [_row_to_lead(r) for r in rows]


@router.get("/{lead_id}")
def get_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, email, phone, company, status, source, score, created_by, created_at, updated_at "
                "FROM leads WHERE id = %s",
                (lead_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _row_to_lead(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_lead(body: LeadBody, current_user: dict = Depends(get_current_user)):
    created_by = body.createdBy or current_user["id"]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO leads (tenant_id, name, email, phone, company, status, source, score, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING id, tenant_id, name, email, phone, company, status, source, score, created_by, created_at, updated_at",
                (body.tenantId, body.name, body.email, body.phone, body.company,
                 body.status, body.source, body.score, created_by)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_lead(row)


@router.put("/{lead_id}")
def update_lead(lead_id: str, body: LeadBody, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE leads SET name=%s, email=%s, phone=%s, company=%s, status=%s, source=%s, score=%s, updated_at=NOW() "
                "WHERE id=%s "
                "RETURNING id, tenant_id, name, email, phone, company, status, source, score, created_by, created_at, updated_at",
                (body.name, body.email, body.phone, body.company, body.status, body.source, body.score, lead_id)
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _row_to_lead(row)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM leads WHERE id = %s", (lead_id,))
        conn.commit()
    return None
