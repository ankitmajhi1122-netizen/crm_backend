"""
main.py — FastAPI application entry point.
Run with: uvicorn main:app --host 0.0.0.0 --port 3000 --reload
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from routers import auth, users, tenants, plans, leads, contacts, accounts, deals, tasks, campaigns, products, quotes, invoices, orders

from contextlib import asynccontextmanager
from db import run_schema

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Apply schema on startup
    try:
        print("🚀 Applying database schema...")
        run_schema()
        print("✅ Database schema applied.")
    except Exception as e:
        print(f"❌ Failed to apply schema on startup: {e}")
        # We don't raise here to allow the app to start even if DB is temporarily down,
        # but the first request will fail if tables are missing.
    yield

app = FastAPI(
    title="CRM API",
    description="Backend REST API for the Frontend CRM application",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL, 
        "https://frontendcrm-production.up.railway.app",
        "http://frontendcrm-production.up.railway.app",
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:4173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(auth.router,      prefix=f"{PREFIX}/auth",      tags=["Auth"])
app.include_router(users.router,     prefix=f"{PREFIX}/users",     tags=["Users"])
app.include_router(tenants.router,   prefix=f"{PREFIX}/tenants",   tags=["Tenants"])
app.include_router(plans.router,     prefix=f"{PREFIX}/plans",     tags=["Plans"])
app.include_router(leads.router,     prefix=f"{PREFIX}/leads",     tags=["Leads"])
app.include_router(contacts.router,  prefix=f"{PREFIX}/contacts",  tags=["Contacts"])
app.include_router(accounts.router,  prefix=f"{PREFIX}/accounts",  tags=["Accounts"])
app.include_router(deals.router,     prefix=f"{PREFIX}/deals",     tags=["Deals"])
app.include_router(tasks.router,     prefix=f"{PREFIX}/tasks",     tags=["Tasks"])
app.include_router(campaigns.router, prefix=f"{PREFIX}/campaigns", tags=["Campaigns"])
app.include_router(products.router,  prefix=f"{PREFIX}/products",  tags=["Products"])
app.include_router(quotes.router,    prefix=f"{PREFIX}/quotes",    tags=["Quotes"])
app.include_router(invoices.router,  prefix=f"{PREFIX}/invoices",  tags=["Invoices"])
app.include_router(orders.router,    prefix=f"{PREFIX}/orders",    tags=["Orders"])


@app.get(f"{PREFIX}/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", os.getenv("PORT", "3000")))
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=port,
        reload=True,
    )
