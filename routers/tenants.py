"""
routers/tenants.py
GET    /tenants/:id
POST   /tenants
PATCH  /tenants/:id
GET    /tenants/:id/subscription
POST   /tenants/:id/subscription
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from db import get_conn
from dependencies import get_current_user

router = APIRouter()


def _row_to_tenant(row) -> dict:
    return {
        "id": row[0], "name": row[1], "domain": row[2] or "",
        "plan": "enterprise",    # Hardcoded for simplification
        "status": "active",      # Hardcoded for simplification
        "logoUrl": row[5] or "",
        "primaryColor": row[6] or "#6366f1", "darkMode": row[7],
        "createdAt": str(row[8]), "updatedAt": str(row[9]),
    }


def _row_to_sub(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], 
        "plan": "enterprise",    # Hardcoded for simplification
        "status": "active",      # Hardcoded for simplification
        "maxUsers": 9999,
        "expiryDate": str(row[5]) if row[5] else None,
        "features": ["dashboard", "leads", "contacts", "accounts", "deals", "activities", "campaigns", "products", "quotes", "invoices", "orders", "forecasting", "reports", "settings"],
        "createdAt": str(row[7]), "updatedAt": str(row[8]),
    }


class CreateTenantBody(BaseModel):
    name: str
    domain: Optional[str] = ""
    plan: Optional[str] = "basic"


class UpdateTenantBody(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    logoUrl: Optional[str] = None
    primaryColor: Optional[str] = None
    darkMode: Optional[bool] = None


class UpdateSubscriptionBody(BaseModel):
    plan: str


@router.get("/{tenant_id}")
def get_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, domain, plan, status, logo_url, primary_color, dark_mode, created_at, updated_at "
                "FROM tenants WHERE id = %s",
                (tenant_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _row_to_tenant(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_tenant(body: CreateTenantBody):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (name, domain, plan) VALUES (%s, %s, %s) "
                "RETURNING id, name, domain, plan, status, logo_url, primary_color, dark_mode, created_at, updated_at",
                (body.name, body.domain, body.plan)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_tenant(row)


@router.patch("/{tenant_id}")
def update_tenant(tenant_id: str, body: UpdateTenantBody, current_user: dict = Depends(get_current_user)):
    fields, vals = [], []
    if body.name is not None: fields.append("name = %s"); vals.append(body.name)
    if body.domain is not None: fields.append("domain = %s"); vals.append(body.domain)
    if body.logoUrl is not None: fields.append("logo_url = %s"); vals.append(body.logoUrl)
    if body.primaryColor is not None: fields.append("primary_color = %s"); vals.append(body.primaryColor)
    if body.darkMode is not None: fields.append("dark_mode = %s"); vals.append(body.darkMode)
    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")
    fields.append("updated_at = NOW()")
    vals.append(tenant_id)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE tenants SET {', '.join(fields)} WHERE id = %s "
                "RETURNING id, name, domain, plan, status, logo_url, primary_color, dark_mode, created_at, updated_at",
                vals
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _row_to_tenant(row)


@router.get("/{tenant_id}/subscription")
def get_subscription(tenant_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, plan, status, max_users, expiry_date, features, created_at, updated_at "
                "FROM subscriptions WHERE tenant_id = %s ORDER BY created_at DESC LIMIT 1",
                (tenant_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return _row_to_sub(row)


@router.post("/{tenant_id}/subscription")
def update_subscription(tenant_id: str, body: UpdateSubscriptionBody, current_user: dict = Depends(get_current_user)):
    plan_limits = {"basic": 5, "pro": 25, "enterprise": 999}
    max_users = plan_limits.get(body.plan, 5)
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Upsert subscription
            cur.execute(
                "UPDATE subscriptions SET plan = %s, max_users = %s, updated_at = NOW() WHERE tenant_id = %s "
                "RETURNING id, tenant_id, plan, status, max_users, expiry_date, features, created_at, updated_at",
                (body.plan, max_users, tenant_id)
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO subscriptions (tenant_id, plan, max_users) VALUES (%s, %s, %s) "
                    "RETURNING id, tenant_id, plan, status, max_users, expiry_date, features, created_at, updated_at",
                    (tenant_id, body.plan, max_users)
                )
                row = cur.fetchone()
            # Update tenant plan too
            cur.execute("UPDATE tenants SET plan = %s, updated_at = NOW() WHERE id = %s", (body.plan, tenant_id))
        conn.commit()
    return _row_to_sub(row)
