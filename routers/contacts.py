"""
routers/contacts.py
GET    /contacts?tenantId=xxx
GET    /contacts/:id
POST   /contacts
PUT    /contacts/:id
DELETE /contacts/:id
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _row_to_contact(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "firstName": row[2], "lastName": row[3],
        "email": row[4], "phone": row[5], "company": row[6],
        "accountId": row[7] or "", "status": row[8],
        "createdBy": row[9] or "", "createdAt": str(row[10]), "updatedAt": str(row[11]),
    }


class ContactBody(BaseModel):
    tenantId: str
    firstName: str
    lastName: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    company: Optional[str] = ""
    accountId: Optional[str] = None
    status: Optional[str] = "active"
    createdBy: Optional[str] = None


@router.get("")
def get_contacts(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, first_name, last_name, email, phone, company, account_id, status, created_by, created_at, updated_at "
                "FROM contacts WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
    return [_row_to_contact(r) for r in rows]


@router.get("/{contact_id}")
def get_contact(contact_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, first_name, last_name, email, phone, company, account_id, status, created_by, created_at, updated_at "
                "FROM contacts WHERE id = %s",
                (contact_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _row_to_contact(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_contact(body: ContactBody, current_user: dict = Depends(get_current_user)):
    created_by = body.createdBy or current_user["id"]
    account_id = body.accountId or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO contacts (tenant_id, first_name, last_name, email, phone, company, account_id, status, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING id, tenant_id, first_name, last_name, email, phone, company, account_id, status, created_by, created_at, updated_at",
                (body.tenantId, body.firstName, body.lastName, body.email, body.phone,
                 body.company, account_id, body.status, created_by)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_contact(row)


@router.put("/{contact_id}")
def update_contact(contact_id: str, body: ContactBody, current_user: dict = Depends(get_current_user)):
    account_id = body.accountId or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE contacts SET first_name=%s, last_name=%s, email=%s, phone=%s, company=%s, account_id=%s, status=%s, updated_at=NOW() "
                "WHERE id=%s "
                "RETURNING id, tenant_id, first_name, last_name, email, phone, company, account_id, status, created_by, created_at, updated_at",
                (body.firstName, body.lastName, body.email, body.phone, body.company, account_id, body.status, contact_id)
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _row_to_contact(row)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
        conn.commit()
    return None
