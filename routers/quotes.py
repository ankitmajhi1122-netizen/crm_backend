"""
routers/quotes.py
GET    /quotes?tenantId=xxx
GET    /quotes/:id
POST   /quotes
PUT    /quotes/:id
DELETE /quotes/:id
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _get_items(conn, quote_id: str) -> list:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT product_id, name, qty, price FROM quote_items WHERE quote_id = %s",
            (quote_id,)
        )
        return [{"productId": r[0] or "", "name": r[1], "qty": r[2], "price": float(r[3])} for r in cur.fetchall()]


def _row_to_quote(row, items=None) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "number": row[2],
        "contactId": row[3] or "", "contactName": row[4] or "",
        "dealId": row[5] or "", "amount": float(row[6] or 0),
        "status": row[7],
        "validUntil": str(row[8]) if row[8] else "",
        "items": items or [],
        "createdBy": row[9] or "", "createdAt": str(row[10]), "updatedAt": str(row[11]),
    }


class QuoteItemBody(BaseModel):
    productId: Optional[str] = ""
    name: str
    qty: int = 1
    price: float = 0


class QuoteBody(BaseModel):
    tenantId: str
    number: str
    contactId: Optional[str] = None
    contactName: Optional[str] = ""
    dealId: Optional[str] = None
    amount: Optional[float] = 0
    status: Optional[str] = "draft"
    validUntil: Optional[str] = None
    items: Optional[List[QuoteItemBody]] = []
    createdBy: Optional[str] = None


@router.get("")
def get_quotes(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, number, contact_id, contact_name, deal_id, amount, status, valid_until, created_by, created_at, updated_at "
                "FROM quotes WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
        result = []
        for r in rows:
            items = _get_items(conn, r[0])
            result.append(_row_to_quote(r, items))
    return result


@router.get("/{quote_id}")
def get_quote(quote_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, number, contact_id, contact_name, deal_id, amount, status, valid_until, created_by, created_at, updated_at "
                "FROM quotes WHERE id = %s",
                (quote_id,)
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Quote not found")
        items = _get_items(conn, quote_id)
    return _row_to_quote(row, items)


def _upsert_items(conn, quote_id: str, items: list):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM quote_items WHERE quote_id = %s", (quote_id,))
        for item in items:
            cur.execute(
                "INSERT INTO quote_items (quote_id, product_id, name, qty, price) VALUES (%s,%s,%s,%s,%s)",
                (quote_id, item.productId or None, item.name, item.qty, item.price)
            )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_quote(body: QuoteBody, current_user: dict = Depends(get_current_user)):
    created_by = body.createdBy or current_user["id"]
    contact_id = body.contactId or None
    deal_id = body.dealId or None
    valid_until = body.validUntil or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO quotes (tenant_id, number, contact_id, contact_name, deal_id, amount, status, valid_until, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING id, tenant_id, number, contact_id, contact_name, deal_id, amount, status, valid_until, created_by, created_at, updated_at",
                (body.tenantId, body.number, contact_id, body.contactName, deal_id,
                 body.amount, body.status, valid_until, created_by)
            )
            row = cur.fetchone()
        _upsert_items(conn, row[0], body.items or [])
        conn.commit()
        items = _get_items(conn, row[0])
    return _row_to_quote(row, items)


@router.put("/{quote_id}")
def update_quote(quote_id: str, body: QuoteBody, current_user: dict = Depends(get_current_user)):
    contact_id = body.contactId or None
    deal_id = body.dealId or None
    valid_until = body.validUntil or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE quotes SET number=%s, contact_id=%s, contact_name=%s, deal_id=%s, amount=%s, status=%s, valid_until=%s, updated_at=NOW() "
                "WHERE id=%s "
                "RETURNING id, tenant_id, number, contact_id, contact_name, deal_id, amount, status, valid_until, created_by, created_at, updated_at",
                (body.number, contact_id, body.contactName, deal_id, body.amount,
                 body.status, valid_until, quote_id)
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Quote not found")
        _upsert_items(conn, quote_id, body.items or [])
        conn.commit()
        items = _get_items(conn, quote_id)
    return _row_to_quote(row, items)


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quote(quote_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM quotes WHERE id = %s", (quote_id,))
        conn.commit()
    return None
