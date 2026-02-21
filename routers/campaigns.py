"""
routers/campaigns.py
GET    /campaigns?tenantId=xxx
GET    /campaigns/:id
POST   /campaigns
PUT    /campaigns/:id
DELETE /campaigns/:id
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _row_to_campaign(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "name": row[2], "type": row[3],
        "status": row[4], "leads": row[5] or 0, "converted": row[6] or 0,
        "budget": float(row[7] or 0), "spent": float(row[8] or 0),
        "startDate": str(row[9]) if row[9] else "",
        "endDate": str(row[10]) if row[10] else "",
        "createdBy": row[11] or "", "createdAt": str(row[12]), "updatedAt": str(row[13]),
    }


class CampaignBody(BaseModel):
    tenantId: str
    name: str
    type: Optional[str] = "Email"
    status: Optional[str] = "draft"
    leads: Optional[int] = 0
    converted: Optional[int] = 0
    budget: Optional[float] = 0
    spent: Optional[float] = 0
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    createdBy: Optional[str] = None


@router.get("")
def get_campaigns(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, type, status, leads, converted, budget, spent, start_date, end_date, created_by, created_at, updated_at "
                "FROM campaigns WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
    return [_row_to_campaign(r) for r in rows]


@router.get("/{campaign_id}")
def get_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, type, status, leads, converted, budget, spent, start_date, end_date, created_by, created_at, updated_at "
                "FROM campaigns WHERE id = %s",
                (campaign_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _row_to_campaign(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_campaign(body: CampaignBody, current_user: dict = Depends(get_current_user)):
    created_by = body.createdBy or current_user["id"]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO campaigns (tenant_id, name, type, status, leads, converted, budget, spent, start_date, end_date, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING id, tenant_id, name, type, status, leads, converted, budget, spent, start_date, end_date, created_by, created_at, updated_at",
                (body.tenantId, body.name, body.type, body.status, body.leads, body.converted,
                 body.budget, body.spent, body.startDate, body.endDate, created_by)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_campaign(row)


@router.put("/{campaign_id}")
def update_campaign(campaign_id: str, body: CampaignBody, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE campaigns SET name=%s, type=%s, status=%s, leads=%s, converted=%s, budget=%s, spent=%s, start_date=%s, end_date=%s, updated_at=NOW() "
                "WHERE id=%s "
                "RETURNING id, tenant_id, name, type, status, leads, converted, budget, spent, start_date, end_date, created_by, created_at, updated_at",
                (body.name, body.type, body.status, body.leads, body.converted,
                 body.budget, body.spent, body.startDate, body.endDate, campaign_id)
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _row_to_campaign(row)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM campaigns WHERE id = %s", (campaign_id,))
        conn.commit()
    return None
