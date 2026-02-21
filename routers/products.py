"""
routers/products.py
GET    /products?tenantId=xxx
GET    /products/:id
POST   /products
PUT    /products/:id
DELETE /products/:id
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _row_to_product(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "name": row[2], "sku": row[3] or "",
        "price": float(row[4] or 0), "category": row[5] or "",
        "status": row[6] or "active", "description": row[7] or "",
        "stock": row[8] or 0, "createdBy": row[9] or "",
        "createdAt": str(row[10]), "updatedAt": str(row[11]),
    }


class ProductBody(BaseModel):
    tenantId: str
    name: str
    sku: Optional[str] = ""
    price: Optional[float] = 0
    category: Optional[str] = ""
    status: Optional[str] = "active"
    description: Optional[str] = ""
    stock: Optional[int] = 0
    createdBy: Optional[str] = None


@router.get("")
def get_products(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, sku, price, category, status, description, stock, created_by, created_at, updated_at "
                "FROM products WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
    return [_row_to_product(r) for r in rows]


@router.get("/{product_id}")
def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, sku, price, category, status, description, stock, created_by, created_at, updated_at "
                "FROM products WHERE id = %s",
                (product_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return _row_to_product(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_product(body: ProductBody, current_user: dict = Depends(get_current_user)):
    created_by = body.createdBy or current_user["id"]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO products (tenant_id, name, sku, price, category, status, description, stock, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING id, tenant_id, name, sku, price, category, status, description, stock, created_by, created_at, updated_at",
                (body.tenantId, body.name, body.sku, body.price, body.category,
                 body.status, body.description, body.stock, created_by)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_product(row)


@router.put("/{product_id}")
def update_product(product_id: str, body: ProductBody, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE products SET name=%s, sku=%s, price=%s, category=%s, status=%s, description=%s, stock=%s, updated_at=NOW() "
                "WHERE id=%s "
                "RETURNING id, tenant_id, name, sku, price, category, status, description, stock, created_by, created_at, updated_at",
                (body.name, body.sku, body.price, body.category, body.status,
                 body.description, body.stock, product_id)
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return _row_to_product(row)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()
    return None
