"""
routers/users.py
GET    /users?tenantId=xxx
GET    /users/:id
POST   /users
PATCH  /users/:id
DELETE /users/:id
POST   /users/:id/reset-password
POST   /users/:id/change-password
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext
from db import get_conn
from dependencies import get_current_user
from utils.email_utils import send_welcome_email
import os

router = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _row_to_user(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "name": row[2],
        "email": row[3], "role": row[4], "status": row[5],
        "avatarUrl": row[6] or "", "createdAt": str(row[7]), "updatedAt": str(row[8]),
    }


class CreateUserBody(BaseModel):
    tenantId: str
    name: str
    email: str
    role: str = "SALES"
    password: str
    mustResetPassword: bool = True


class UpdateUserBody(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class ResetPasswordBody(BaseModel):
    newPassword: str


class ChangePasswordBody(BaseModel):
    currentPassword: str
    newPassword: str


@router.get("")
def get_users(tenantId: str = Query(...), current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, email, role, status, avatar_url, created_at, updated_at "
                "FROM users WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenantId,)
            )
            rows = cur.fetchall()
    return [_row_to_user(r) for r in rows]


@router.get("/{user_id}")
def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, email, role, status, avatar_url, created_at, updated_at "
                "FROM users WHERE id = %s",
                (user_id,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return _row_to_user(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(body: CreateUserBody, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("ADMIN",):
        raise HTTPException(status_code=403, detail="Admin role required")
    # Truncate to 72 bytes for bcrypt compatibility
    safe_password = body.password.encode('utf-8')[:72].decode('utf-8', 'ignore')
    pw_hash = pwd_ctx.hash(safe_password)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (tenant_id, name, email, password_hash, role, must_reset_password) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "RETURNING id, tenant_id, name, email, role, status, avatar_url, created_at, updated_at",
                (body.tenantId, body.name, body.email, pw_hash, body.role, body.mustResetPassword)
            )
            row = cur.fetchone()
        conn.commit()
    try:
        send_welcome_email(body.email, body.name, body.password)
    except Exception as e:
        print(f"Welcome email error: {e}")
    return _row_to_user(row)


@router.patch("/{user_id}")
def update_user(user_id: str, body: UpdateUserBody, current_user: dict = Depends(get_current_user)):
    fields, vals = [], []
    if body.name is not None:
        fields.append("name = %s"); vals.append(body.name)
    if body.role is not None:
        fields.append("role = %s"); vals.append(body.role)
    if body.status is not None:
        fields.append("status = %s"); vals.append(body.status)
    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")
    fields.append("updated_at = NOW()")
    vals.append(user_id)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE id = %s "
                "RETURNING id, tenant_id, name, email, role, status, avatar_url, created_at, updated_at",
                vals
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return _row_to_user(row)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin role required")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    return None


@router.post("/{user_id}/reset-password")
def admin_reset_password(user_id: str, body: ResetPasswordBody, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin role required")
    pw_hash = pwd_ctx.hash(body.newPassword)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, must_reset_password = true, updated_at = NOW() WHERE id = %s "
                "RETURNING id, tenant_id, name, email, role, status, avatar_url, created_at, updated_at",
                (pw_hash, user_id)
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return _row_to_user(row)


@router.post("/{user_id}/change-password")
def change_password(user_id: str, body: ChangePasswordBody, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    # Truncate to 72 bytes for bcrypt compatibility
    safe_current = body.currentPassword.encode('utf-8')[:72].decode('utf-8', 'ignore')
    if not pwd_ctx.verify(safe_current, row[0]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    pw_hash = pwd_ctx.hash(body.newPassword)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, must_reset_password = false, updated_at = NOW() WHERE id = %s "
                "RETURNING id, tenant_id, name, email, role, status, avatar_url, created_at, updated_at",
                (pw_hash, user_id)
            )
            row = cur.fetchone()
        conn.commit()
    return _row_to_user(row)
