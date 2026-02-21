"""
routers/plans.py
GET /plans
GET /plans/:plan
"""
from fastapi import APIRouter, HTTPException
from db import get_conn

router = APIRouter()


def _row_to_plan(row) -> dict:
    return {
        "plan": row[0], "label": row[1], "subtitle": row[2],
        "maxUsers": row[3], "monthlyPrice": float(row[4]),
        "features": row[5] or [],
        "featureLabels": row[6] or [],
    }


@router.get("")
def get_plans():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT plan, label, subtitle, max_users, monthly_price, features, feature_labels FROM plans ORDER BY monthly_price"
            )
            rows = cur.fetchall()
    return [_row_to_plan(r) for r in rows]


@router.get("/{plan_key}")
def get_plan(plan_key: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT plan, label, subtitle, max_users, monthly_price, features, feature_labels FROM plans WHERE plan = %s",
                (plan_key,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _row_to_plan(row)
