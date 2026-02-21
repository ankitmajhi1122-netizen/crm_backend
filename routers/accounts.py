"""
routers/accounts.py
GET    /accounts?tenantId=xxx
GET    /accounts/:id
POST   /accounts
PUT    /accounts/:id
DELETE /accounts/:id
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _row_to_account(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "name": row[2], "industry": row[3] or "",
        "website": row[4] or "", "phone": row[5] or "", "email": row[6] or "",
        "revenue": float(row[7] or 0), "employees": row[8] or 0, "status": row[9] or "active",
        "ownerId": row[10] or "", "createdBy": row[11] or "",
        "createdAt": str(row[12]), "updatedAt": str(row[13]),
    }


class AccountBody(BaseModel):
    tenantId: str
    name: str
    industry: Optional[str] = ""
    website: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    revenue: Optional[float] = 0
    employees: Optional[int] = 0
    status: Optional[str] = "active"
    ownerId: Optional[str] = None
    createdBy: Optional[str] = None


@router.get("")
def get_accounts(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, industry, website, phone, email, revenue, employees, status, owner_id, created_by, created_at, updated_at "
                "FROM accounts WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
    return [_row_to_account(r) for r in rows]


@router.get("/{account_id}")
def get_account(account_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, industry, website, phone, email, revenue, employees, status, owner_id, created_by, created_at, updated_at "
                "FROM accounts WHERE id = %s",
                (account_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    return _row_to_account(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_account(body: AccountBody, current_user: dict = Depends(get_current_user)):
    created_by = body.createdBy or current_user["id"]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (tenant_id, name, industry, website, phone, email, revenue, employees, status, owner_id, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING id, tenant_id, name, industry, website, phone, email, revenue, employees, status, owner_id, created_by, created_at, updated_at",
                (body.tenantId, body.name, body.industry, body.website, body.phone, body.email,
                 body.revenue, body.employees, body.status, body.ownerId, created_by)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_account(row)


@router.put("/{account_id}")
def update_account(account_id: str, body: AccountBody, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE accounts SET name=%s, industry=%s, website=%s, phone=%s, email=%s, revenue=%s, employees=%s, status=%s, owner_id=%s, updated_at=NOW() "
                "WHERE id=%s "
                "RETURNING id, tenant_id, name, industry, website, phone, email, revenue, employees, status, owner_id, created_by, created_at, updated_at",
                (body.name, body.industry, body.website, body.phone, body.email,
                 body.revenue, body.employees, body.status, body.ownerId, account_id)
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    return _row_to_account(row)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM accounts WHERE id = %s", (account_id,))
        conn.commit()
    return None
