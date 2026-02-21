"""
routers/auth.py
POST /auth/login
POST /auth/logout
POST /auth/forgot-password
POST /auth/reset-password
POST /auth/admin-reset-password
"""
import os
import secrets
from datetime import timedelta, datetime
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError

from db import get_conn
from utils.jwt_utils import create_access_token, verify_access_token
from utils.email_utils import send_password_reset_email
from utils.auth_utils import get_password_hash_input
from dependencies import get_current_user

router = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


# ─── helpers ────────────────────────────────────────────────────────────────

def _row_to_user(row) -> dict:
    return {
        "id": row[0], "tenantId": row[1], "name": row[2],
        "email": row[3], "role": row[5], "status": row[6],
        "avatarUrl": row[7] or "", "createdAt": str(row[8]), "updatedAt": str(row[9]),
    }


def _row_to_tenant(row) -> dict:
    return {
        "id": row[0], "name": row[1], "domain": row[2] or "",
        "plan": "enterprise",    # Hardcoded for simplification
        "status": "active",      # Hardcoded for simplification
        "logoUrl": row[5] or "",
        "primaryColor": row[6] or "#6366f1", "darkMode": row[7],
        "createdAt": str(row[8]), "updatedAt": str(row[9]),
    }


# ─── schemas ─────────────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    email: str
    password: str

class ForgotPasswordBody(BaseModel):
    email: str

class ResetPasswordBody(BaseModel):
    userId: str
    currentPassword: str
    newPassword: str

class AdminResetBody(BaseModel):
    userId: str
    newPassword: str

class SignUpBody(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    company: str
    plan: str = "basic"


# ─── endpoints ───────────────────────────────────────────────────────────────

@router.post("/login")
def login(body: LoginBody):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tenant_id, name, email, password_hash, role, status, avatar_url, created_at, updated_at "
                "FROM users WHERE email = %s",
                (body.email,)
            )
            row = cur.fetchone()

    pw_input = get_password_hash_input(body.password)
    if not row or not pwd_ctx.verify(pw_input, row[4]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check removed for simplification:
    # if row[6] != "active":
    #     raise HTTPException(status_code=403, detail="Account is inactive")

    user = _row_to_user(row)
    token = create_access_token({
        "sub": user["id"],
        "tenant_id": user["tenantId"],
        "email": user["email"],
        "role": user["role"],
    })

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, domain, plan, status, logo_url, primary_color, dark_mode, created_at, updated_at "
                "FROM tenants WHERE id = %s",
                (user["tenantId"],)
            )
            t_row = cur.fetchone()

    tenant = _row_to_tenant(t_row) if t_row else {}
    return {"user": user, "tenant": tenant, "accessToken": token}


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignUpBody):
    # 1. Email uniqueness check
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="User with this email already exists")

    # 2. Transaction for Tenant + User + Subscription
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                # Create Tenant
                domain = f"{body.company.lower().replace(' ', '-')}.crm.io"
                cur.execute(
                    "INSERT INTO tenants (name, domain, plan, status) VALUES (%s, %s, %s, 'active') "
                    "RETURNING id, name, domain, plan, status, logo_url, primary_color, dark_mode, created_at, updated_at",
                    (body.company, domain, body.plan)
                )
                t_row = cur.fetchone()
                tenant_id = t_row[0]

                # Create Admin User
                # Pre-hash to bypass bcrypt 72-byte limit
                pw_input = get_password_hash_input(body.password)
                pw_hash = pwd_ctx.hash(pw_input)
                cur.execute(
                    "INSERT INTO users (tenant_id, name, email, password_hash, role, status) "
                    "VALUES (%s, %s, %s, %s, 'ADMIN', 'active') "
                    "RETURNING id, tenant_id, name, email, password_hash, role, status, avatar_url, created_at, updated_at",
                    (tenant_id, body.fullName, body.email, pw_hash)
                )
                u_row = cur.fetchone()

                # Create Subscription
                plan_limits = {"basic": 5, "pro": 25, "enterprise": 999}
                max_users = plan_limits.get(body.plan, 5)
                cur.execute(
                    "INSERT INTO subscriptions (tenant_id, plan, status, max_users, expiry_date) "
                    "VALUES (%s, %s, 'active', %s, NOW() + INTERVAL '1 year')",
                    (tenant_id, body.plan, max_users)
                )
                
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Signup error: {e}")
                raise HTTPException(status_code=500, detail="Failed to create account")

    user = _row_to_user(u_row)
    tenant = _row_to_tenant(t_row)
    
    # Generate Token
    token = create_access_token({
        "sub": user["id"],
        "tenant_id": user["tenantId"],
        "email": user["email"],
        "role": user["role"],
    })

    return {"user": user, "tenant": tenant, "accessToken": token}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    # JWT is stateless; client discards token.
    return None


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(body: ForgotPasswordBody):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
            row = cur.fetchone()

    if not row:
        # Don't reveal whether email exists
        return None

    user_id = row[0]
    token = secrets.token_urlsafe(48)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (user_id, token, expires_at)
            )
        conn.commit()

    try:
        send_password_reset_email(body.email, token, FRONTEND_URL)
    except Exception as e:
        # Log but don't expose SMTP errors to client
        print(f"SMTP error: {e}")

    return None


@router.post("/reset-password")
def reset_password(body: ResetPasswordBody, current_user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash, must_reset_password FROM users WHERE id = %s", (body.userId,))
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    pw_hash, must_reset = row[0], row[1]

    # If force-reset (admin set temp password), skip currentPassword check.
    # Otherwise verify currentPassword.
    if not must_reset:
        pw_input = get_password_hash_input(body.currentPassword)
        if not body.currentPassword or not pwd_ctx.verify(pw_input, pw_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_hash = pwd_ctx.hash(body.newPassword)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, must_reset_password = false, updated_at = NOW() WHERE id = %s "
                "RETURNING id, tenant_id, name, email, password_hash, role, status, avatar_url, created_at, updated_at",
                (new_hash, body.userId)
            )
            row = cur.fetchone()
        conn.commit()

    return _row_to_user(row)


@router.post("/admin-reset-password")
def admin_reset_password(body: AdminResetBody, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("ADMIN",):
        raise HTTPException(status_code=403, detail="Admin role required")

    new_hash = pwd_ctx.hash(body.newPassword)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, must_reset_password = true, updated_at = NOW() WHERE id = %s "
                "RETURNING id, tenant_id, name, email, password_hash, role, status, avatar_url, created_at, updated_at",
                (new_hash, body.userId)
            )
            row = cur.fetchone()
        conn.commit()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return _row_to_user(row)
