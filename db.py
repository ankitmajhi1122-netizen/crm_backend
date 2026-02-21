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

# Connection pool (1-10 connections)
connection_pool = pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)


@contextmanager
def get_conn():
    """Context manager that yields a psycopg2 connection from the pool."""
    conn = connection_pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        connection_pool.putconn(conn)


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
