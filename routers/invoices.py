"""
routers/invoices.py
GET    /invoices?tenantId=xxx
GET    /invoices/:id
POST   /invoices
PUT    /invoices/:id
DELETE /invoices/:id
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _row_to_invoice(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "number": row[2],
        "contactId": row[3] or "", "client": row[4] or "",
        "amount": float(row[5] or 0), "tax": float(row[6] or 0), "total": float(row[7] or 0),
        "dueDate": str(row[8]) if row[8] else "",
        "status": row[9], "quoteId": row[10],
        "createdBy": row[11] or "", "createdAt": str(row[12]), "updatedAt": str(row[13]),
    }


class InvoiceBody(BaseModel):
    tenantId: str
    number: str
    contactId: Optional[str] = None
    client: Optional[str] = ""
    amount: Optional[float] = 0
    tax: Optional[float] = 0
    total: Optional[float] = 0
    dueDate: Optional[str] = None
    status: Optional[str] = "draft"
    quoteId: Optional[str] = None
    createdBy: Optional[str] = None


@router.get("")
def get_invoices(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, number, contact_id, client, amount, tax, total, due_date, status, quote_id, created_by, created_at, updated_at "
                "FROM invoices WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
    return [_row_to_invoice(r) for r in rows]


@router.get("/{invoice_id}")
def get_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, number, contact_id, client, amount, tax, total, due_date, status, quote_id, created_by, created_at, updated_at "
                "FROM invoices WHERE id = %s",
                (invoice_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _row_to_invoice(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_invoice(body: InvoiceBody, current_user: dict = Depends(get_current_user)):
    created_by = body.createdBy or current_user["id"]
    contact_id = body.contactId or None
    quote_id = body.quoteId or None
    due_date = body.dueDate or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO invoices (tenant_id, number, contact_id, client, amount, tax, total, due_date, status, quote_id, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING id, tenant_id, number, contact_id, client, amount, tax, total, due_date, status, quote_id, created_by, created_at, updated_at",
                (body.tenantId, body.number, contact_id, body.client, body.amount,
                 body.tax, body.total, due_date, body.status, quote_id, created_by)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_invoice(row)


@router.put("/{invoice_id}")
def update_invoice(invoice_id: str, body: InvoiceBody, current_user: dict = Depends(get_current_user)):
    contact_id = body.contactId or None
    quote_id = body.quoteId or None
    due_date = body.dueDate or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE invoices SET number=%s, contact_id=%s, client=%s, amount=%s, tax=%s, total=%s, due_date=%s, status=%s, quote_id=%s, updated_at=NOW() "
                "WHERE id=%s "
                "RETURNING id, tenant_id, number, contact_id, client, amount, tax, total, due_date, status, quote_id, created_by, created_at, updated_at",
                (body.number, contact_id, body.client, body.amount, body.tax,
                 body.total, due_date, body.status, quote_id, invoice_id)
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _row_to_invoice(row)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM invoices WHERE id = %s", (invoice_id,))
        conn.commit()
    return None
