"""
routers/orders.py
GET    /orders?tenantId=xxx
GET    /orders/:id
POST   /orders
PUT    /orders/:id
DELETE /orders/:id
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _row_to_order(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "number": row[2],
        "contactId": row[3] or "", "client": row[4] or "",
        "items": row[5] or 0,
        "subtotal": float(row[6] or 0), "tax": float(row[7] or 0), "total": float(row[8] or 0),
        "status": row[9],
        "orderDate": str(row[10]) if row[10] else "",
        "deliveryDate": str(row[11]) if row[11] else None,
        "createdBy": row[12] or "", "createdAt": str(row[13]), "updatedAt": str(row[14]),
    }


class OrderBody(BaseModel):
    tenantId: str
    number: str
    contactId: Optional[str] = None
    client: Optional[str] = ""
    items: Optional[int] = 0
    subtotal: Optional[float] = 0
    tax: Optional[float] = 0
    total: Optional[float] = 0
    status: Optional[str] = "pending"
    orderDate: Optional[str] = None
    deliveryDate: Optional[str] = None
    createdBy: Optional[str] = None


@router.get("")
def get_orders(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, number, contact_id, client, items, subtotal, tax, total, status, order_date, delivery_date, created_by, created_at, updated_at "
                "FROM orders WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
    return [_row_to_order(r) for r in rows]


@router.get("/{order_id}")
def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, number, contact_id, client, items, subtotal, tax, total, status, order_date, delivery_date, created_by, created_at, updated_at "
                "FROM orders WHERE id = %s",
                (order_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return _row_to_order(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_order(body: OrderBody, current_user: dict = Depends(get_current_user)):
    created_by = body.createdBy or current_user["id"]
    contact_id = body.contactId or None
    order_date = body.orderDate or None
    delivery_date = body.deliveryDate or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (tenant_id, number, contact_id, client, items, subtotal, tax, total, status, order_date, delivery_date, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING id, tenant_id, number, contact_id, client, items, subtotal, tax, total, status, order_date, delivery_date, created_by, created_at, updated_at",
                (body.tenantId, body.number, contact_id, body.client, body.items,
                 body.subtotal, body.tax, body.total, body.status, order_date,
                 delivery_date, created_by)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_order(row)


@router.put("/{order_id}")
def update_order(order_id: str, body: OrderBody, current_user: dict = Depends(get_current_user)):
    contact_id = body.contactId or None
    order_date = body.orderDate or None
    delivery_date = body.deliveryDate or None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE orders SET number=%s, contact_id=%s, client=%s, items=%s, subtotal=%s, tax=%s, total=%s, status=%s, order_date=%s, delivery_date=%s, updated_at=NOW() "
                "WHERE id=%s "
                "RETURNING id, tenant_id, number, contact_id, client, items, subtotal, tax, total, status, order_date, delivery_date, created_by, created_at, updated_at",
                (body.number, contact_id, body.client, body.items, body.subtotal,
                 body.tax, body.total, body.status, order_date, delivery_date, order_id)
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return _row_to_order(row)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))
        conn.commit()
    return None
