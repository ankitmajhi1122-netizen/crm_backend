import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

EXPECTED_TABLES = [
    'tenants', 'subscriptions', 'users', 'leads', 'accounts',
    'contacts', 'deals', 'tasks', 'campaigns', 'products',
    'quotes', 'quote_items', 'invoices', 'orders',
    'plans', 'password_reset_tokens',
]

EXPECTED_FKS = [
    # (from_table, from_col, to_table, to_col)
    ('subscriptions',        'tenant_id',   'tenants',  'id'),
    ('users',                'tenant_id',   'tenants',  'id'),
    ('leads',                'tenant_id',   'tenants',  'id'),
    ('accounts',             'tenant_id',   'tenants',  'id'),
    ('contacts',             'tenant_id',   'tenants',  'id'),
    ('contacts',             'account_id',  'accounts', 'id'),
    ('deals',                'tenant_id',   'tenants',  'id'),
    ('deals',                'contact_id',  'contacts', 'id'),
    ('deals',                'account_id',  'accounts', 'id'),
    ('tasks',                'tenant_id',   'tenants',  'id'),
    ('campaigns',            'tenant_id',   'tenants',  'id'),
    ('products',             'tenant_id',   'tenants',  'id'),
    ('quotes',               'tenant_id',   'tenants',  'id'),
    ('quotes',               'contact_id',  'contacts', 'id'),
    ('quotes',               'deal_id',     'deals',    'id'),
    ('quote_items',          'quote_id',    'quotes',   'id'),
    ('invoices',             'tenant_id',   'tenants',  'id'),
    ('invoices',             'contact_id',  'contacts', 'id'),
    ('invoices',             'quote_id',    'quotes',   'id'),
    ('orders',               'tenant_id',   'tenants',  'id'),
    ('orders',               'contact_id',  'contacts', 'id'),
    ('password_reset_tokens','user_id',     'users',    'id'),
]

def check_db():
    conn_str = os.getenv("DATABASE_URL")
    if not conn_str:
        print("❌  DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True
        cur = conn.cursor()

        print("=" * 60)
        print("  CRM DATABASE RELATIONS AUDIT")
        print("=" * 60)

        # --- 1. Table existence ---
        print("\n[1] TABLE EXISTENCE")
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        actual_tables = {r[0] for r in cur.fetchall()}
        all_ok = True
        for t in EXPECTED_TABLES:
            exists = t in actual_tables
            status = "✅" if exists else "❌ MISSING"
            print(f"  {status}  {t}")
            if not exists:
                all_ok = False
        extra = actual_tables - set(EXPECTED_TABLES)
        if extra:
            print(f"  ℹ️  Extra tables (not in schema): {extra}")

        # --- 2. Foreign key constraints ---
        print("\n[2] FOREIGN KEY CONSTRAINTS")
        cur.execute("""
            SELECT
                tc.table_name  AS from_table,
                kcu.column_name AS from_col,
                ccu.table_name  AS to_table,
                ccu.column_name AS to_col
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name
        """)
        actual_fks = set(cur.fetchall())
        expected_set = set(EXPECTED_FKS)

        for fk in sorted(expected_set):
            exists = fk in actual_fks
            status = "✅" if exists else "❌ MISSING"
            print(f"  {status}  {fk[0]}.{fk[1]} → {fk[2]}.{fk[3]}")

        extra_fks = actual_fks - expected_set
        if extra_fks:
            print(f"\n  ℹ️  Extra FKs in DB (not expected but present):")
            for fk in sorted(extra_fks):
                print(f"       {fk[0]}.{fk[1]} → {fk[2]}.{fk[3]}")

        # --- 3. Orphaned data check ---
        print("\n[3] ORPHANED DATA CHECK")

        def check_orphans(from_t, from_col, to_t, to_col):
            cur.execute(f"""
                SELECT COUNT(*) FROM {from_t}
                WHERE {from_col} IS NOT NULL
                  AND {from_col} != ''
                  AND {from_col} NOT IN (SELECT {to_col} FROM {to_t})
            """)
            count = cur.fetchone()[0]
            status = "✅" if count == 0 else f"⚠️  {count} ORPHAN(S)"
            print(f"  {status}  {from_t}.{from_col} → {to_t}.{to_col}")

        # Only check optional FK columns (nullable) since required ones are enforced by DB
        nullable_fk_checks = [
            ('contacts', 'account_id',  'accounts', 'id'),
            ('deals',    'contact_id',  'contacts', 'id'),
            ('deals',    'account_id',  'accounts', 'id'),
            ('quotes',   'contact_id',  'contacts', 'id'),
            ('quotes',   'deal_id',     'deals',    'id'),
            ('invoices', 'contact_id',  'contacts', 'id'),
            ('invoices', 'quote_id',    'quotes',   'id'),
            ('orders',   'contact_id',  'contacts', 'id'),
        ]
        for item in nullable_fk_checks:
            if item[0] in actual_tables and item[2] in actual_tables:
                check_orphans(*item)

        # --- 4. Row counts ---
        print("\n[4] ROW COUNTS")
        for t in EXPECTED_TABLES:
            if t in actual_tables:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                count = cur.fetchone()[0]
                print(f"  {'📋' if count > 0 else '  '}  {t:<25} {count:>6} rows")

        # --- 5. NULL / empty-string issues in TEXT FK columns ---
        print("\n[5] EMPTY-STRING FK SCAN (should all be 0 — nulls are ok, '' is not)")
        text_fk_cols = [
            ('contacts', 'account_id'),
            ('deals',    'contact_id'),
            ('deals',    'account_id'),
            ('quotes',   'contact_id'),
            ('quotes',   'deal_id'),
            ('invoices', 'contact_id'),
            ('invoices', 'quote_id'),
            ('orders',   'contact_id'),
            ('tasks',    'assigned_to'),
        ]
        for t, col in text_fk_cols:
            if t in actual_tables:
                cur.execute(f"SELECT COUNT(*) FROM {t} WHERE {col} = ''")
                count = cur.fetchone()[0]
                status = "✅" if count == 0 else f"⚠️  {count} empty string(s)"
                print(f"  {status}  {t}.{col}")

        print("\n" + "=" * 60)
        print("  AUDIT COMPLETE")
        print("=" * 60 + "\n")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌  DB connection error: {e}")

if __name__ == "__main__":
    check_db()
