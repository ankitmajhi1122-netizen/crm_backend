"""
dependencies.py — FastAPI shared Depends functions.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from utils.jwt_utils import verify_access_token
from db import get_conn

bearer_scheme = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """
    Extract and verify JWT from 'Authorization: Bearer <token>'.
    Returns payload dict: { sub: user_id, tenant_id, email, role }
    """
    token = credentials.credentials
    try:
        payload = verify_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists in DB
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, tenant_id, email, role, status FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()

    # if not row or row[4] != "active":
    #     raise HTTPException(status_code=401, detail="User not found or inactive")
    if not row:
        raise HTTPException(status_code=401, detail="User not found")

    return {"id": row[0], "tenant_id": row[1], "email": row[2], "role": row[3]}
