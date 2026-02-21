"""
routers/deals.py
GET    /deals?tenantId=xxx
GET    /deals/:id
POST   /deals
PUT    /deals/:id
DELETE /deals/:id
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _row_to_deal(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "title": row[2],
        "contactId": row[3] or "", "accountId": row[4] or "",
        "stage": row[5], "value": float(row[6] or 0), "margin": float(row[7] or 0),
        "cost": float(row[8] or 0), "revenue": float(row[9] or 0),
        "probability": row[10] or 0,
        "closeDate": str(row[11]) if row[11] else "",
        "status": row[12], "createdBy": row[13] or "",
        "createdAt": str(row[14]), "updatedAt": str(row[15]),
    }


class DealBody(BaseModel):
    tenantId: str
    title: str
    contactId: Optional[str] = None
    accountId: Optional[str] = None
    stage: Optional[str] = "discovery"
    value: Optional[float] = 0
    margin: Optional[float] = 0
    cost: Optional[float] = 0
    revenue: Optional[float] = 0
    probability: Optional[int] = 0
    closeDate: Optional[str] = None
    status: Optional[str] = "active"
    createdBy: Optional[str] = None


@router.get("")
def get_deals(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, title, contact_id, account_id, stage, value, margin, cost, revenue, probability, close_date, status, created_by, created_at, updated_at "
                "FROM deals WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
    return [_row_to_deal(r) for r in rows]


@router.get("/{deal_id}")
def get_deal(deal_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, title, contact_id, account_id, stage, value, margin, cost, revenue, probability, close_date, status, created_by, created_at, updated_at "
                "FROM deals WHERE id = %s",
                (deal_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _row_to_deal(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_deal(body: DealBody, current_user: dict = Depends(get_current_user)):
    created_by = body.createdBy or current_user["id"]
    close_date = body.closeDate or None
    contact_id = body.contactId or None
    account_id = body.accountId or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO deals (tenant_id, title, contact_id, account_id, stage, value, margin, cost, revenue, probability, close_date, status, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING id, tenant_id, title, contact_id, account_id, stage, value, margin, cost, revenue, probability, close_date, status, created_by, created_at, updated_at",
                (body.tenantId, body.title, contact_id, account_id, body.stage,
                 body.value, body.margin, body.cost, body.revenue, body.probability,
                 close_date, body.status, created_by)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_deal(row)


@router.put("/{deal_id}")
def update_deal(deal_id: str, body: DealBody, current_user: dict = Depends(get_current_user)):
    close_date = body.closeDate or None
    contact_id = body.contactId or None
    account_id = body.accountId or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE deals SET title=%s, contact_id=%s, account_id=%s, stage=%s, value=%s, margin=%s, cost=%s, revenue=%s, probability=%s, close_date=%s, status=%s, updated_at=NOW() "
                "WHERE id=%s "
                "RETURNING id, tenant_id, title, contact_id, account_id, stage, value, margin, cost, revenue, probability, close_date, status, created_by, created_at, updated_at",
                (body.title, contact_id, account_id, body.stage, body.value, body.margin,
                 body.cost, body.revenue, body.probability, close_date, body.status, deal_id)
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _row_to_deal(row)


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(deal_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM deals WHERE id = %s", (deal_id,))
        conn.commit()
    return None
