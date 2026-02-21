"""
db.py — NeonDB PostgreSQL connection pool
Uses psycopg2 with SSL required for NeonDB.
"""
import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Lazy-loaded connection pool
_connection_pool = None

def get_pool():
    global _connection_pool
    if _connection_pool is None:
        if not DATABASE_URL:
            print("❌ CRITICAL ERROR: DATABASE_URL environment variable is not set.")
            print("Please add DATABASE_URL to your environment variables (e.g., in Railway Variables tab).")
            raise EnvironmentError("DATABASE_URL not found.")
        
        try:
            # Ensure sslmode=require for remote connections if not already specified
            dsn = DATABASE_URL
            if "sslmode=" not in dsn and "localhost" not in dsn and "127.0.0.1" not in dsn:
                separator = "&" if "?" in dsn else "?"
                dsn = f"{dsn}{separator}sslmode=require"
                
            print(f"🔌 Initializing database connection pool...")
            _connection_pool = pool.SimpleConnectionPool(1, 10, dsn=dsn)
            print("✅ Database connection pool initialized.")
        except Exception as e:
            print(f"❌ FAILED to initialize database connection pool: {e}")
            raise

    return _connection_pool


@contextmanager
def get_conn():
    """Context manager that yields a psycopg2 connection from the pool."""
    pool_obj = get_pool()
    conn = pool_obj.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        pool_obj.putconn(conn)


def run_schema():
    """Execute schema.sql against the database to create all tables."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        sql = f.read()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("✅ Schema applied successfully.")


if __name__ == "__main__":
    run_schema()
