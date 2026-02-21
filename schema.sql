-- ============================================================
-- CRM Schema — NeonDB (PostgreSQL)
-- Run once via: python db.py   OR   python -c "from db import run_schema; run_schema()"
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------
-- TENANTS (organisations / companies)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id           TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    name         TEXT NOT NULL,
    domain       TEXT,
    plan         TEXT NOT NULL DEFAULT 'basic' CHECK (plan IN ('basic','pro','enterprise')),
    status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','cancelled')),
    logo_url     TEXT DEFAULT '',
    primary_color TEXT DEFAULT '#6366f1',
    dark_mode    BOOLEAN NOT NULL DEFAULT false,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- SUBSCRIPTIONS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscriptions (
    id           TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id    TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan         TEXT NOT NULL DEFAULT 'basic',
    status       TEXT NOT NULL DEFAULT 'active',
    max_users    INT NOT NULL DEFAULT 5,
    expiry_date  TIMESTAMPTZ,
    features     TEXT[] DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- USERS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id           TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    email               TEXT NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,
    role                TEXT NOT NULL DEFAULT 'SALES' CHECK (role IN ('ADMIN','MANAGER','SALES')),
    status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
    avatar_url          TEXT DEFAULT '',
    must_reset_password BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- LEADS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS leads (
    id         TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    email      TEXT DEFAULT '',
    phone      TEXT DEFAULT '',
    company    TEXT DEFAULT '',
    status     TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','contacted','qualified','disqualified')),
    source     TEXT NOT NULL DEFAULT 'other' CHECK (source IN ('web','referral','email','social','other')),
    score      INT NOT NULL DEFAULT 0,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- ACCOUNTS (companies)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS accounts (
    id         TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    industry   TEXT DEFAULT '',
    website    TEXT DEFAULT '',
    phone      TEXT DEFAULT '',
    email      TEXT DEFAULT '',
    revenue    NUMERIC(18,2) DEFAULT 0,
    employees  INT DEFAULT 0,
    status     TEXT DEFAULT 'active',
    owner_id   TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- CONTACTS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS contacts (
    id         TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    first_name TEXT NOT NULL,
    last_name  TEXT NOT NULL,
    email      TEXT DEFAULT '',
    phone      TEXT DEFAULT '',
    company    TEXT DEFAULT '',
    account_id TEXT REFERENCES accounts(id) ON DELETE SET NULL,
    status     TEXT DEFAULT 'active',
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- DEALS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS deals (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    contact_id  TEXT REFERENCES contacts(id) ON DELETE SET NULL,
    account_id  TEXT REFERENCES accounts(id) ON DELETE SET NULL,
    stage       TEXT NOT NULL DEFAULT 'discovery' CHECK (stage IN ('discovery','proposal','negotiation','closed_won','closed_lost')),
    value       NUMERIC(18,2) DEFAULT 0,
    margin      NUMERIC(18,2) DEFAULT 0,
    cost        NUMERIC(18,2) DEFAULT 0,
    revenue     NUMERIC(18,2) DEFAULT 0,
    probability INT DEFAULT 0,
    close_date  DATE,
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','won','lost')),
    created_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- TASKS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    due_date    TIMESTAMPTZ,
    priority    TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high')),
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_progress','done')),
    assigned_to TEXT,
    related_to  TEXT DEFAULT '',
    created_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- CAMPAIGNS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaigns (
    id         TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    type       TEXT NOT NULL DEFAULT 'Email' CHECK (type IN ('Email','Social','Event','Referral','Other')),
    status     TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','done','paused')),
    leads      INT DEFAULT 0,
    converted  INT DEFAULT 0,
    budget     NUMERIC(18,2) DEFAULT 0,
    spent      NUMERIC(18,2) DEFAULT 0,
    start_date DATE,
    end_date   DATE,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- PRODUCTS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    sku         TEXT DEFAULT '',
    price       NUMERIC(18,2) DEFAULT 0,
    category    TEXT DEFAULT '',
    status      TEXT DEFAULT 'active',
    description TEXT DEFAULT '',
    stock       INT DEFAULT 0,
    created_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- QUOTES
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS quotes (
    id           TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id    TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    number       TEXT NOT NULL,
    contact_id   TEXT REFERENCES contacts(id) ON DELETE SET NULL,
    contact_name TEXT DEFAULT '',
    deal_id      TEXT REFERENCES deals(id) ON DELETE SET NULL,
    amount       NUMERIC(18,2) DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','sent','active','done','expired')),
    valid_until  DATE,
    created_by   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- QUOTE ITEMS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS quote_items (
    id         TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    quote_id   TEXT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    product_id TEXT,
    name       TEXT NOT NULL,
    qty        INT NOT NULL DEFAULT 1,
    price      NUMERIC(18,2) NOT NULL DEFAULT 0
);

-- -----------------------------------------------------------
-- INVOICES
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    id         TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    number     TEXT NOT NULL,
    contact_id TEXT REFERENCES contacts(id) ON DELETE SET NULL,
    client     TEXT DEFAULT '',
    amount     NUMERIC(18,2) DEFAULT 0,
    tax        NUMERIC(18,2) DEFAULT 0,
    total      NUMERIC(18,2) DEFAULT 0,
    due_date   DATE,
    status     TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','sent','paid','pending','overdue')),
    quote_id   TEXT REFERENCES quotes(id) ON DELETE SET NULL,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- ORDERS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id            TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    tenant_id     TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    number        TEXT NOT NULL,
    contact_id    TEXT REFERENCES contacts(id) ON DELETE SET NULL,
    client        TEXT DEFAULT '',
    items         INT DEFAULT 0,
    subtotal      NUMERIC(18,2) DEFAULT 0,
    tax           NUMERIC(18,2) DEFAULT 0,
    total         NUMERIC(18,2) DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_progress','done','cancelled')),
    order_date    DATE,
    delivery_date DATE,
    created_by    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- PLANS (static catalogue)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS plans (
    plan          TEXT PRIMARY KEY,
    label         TEXT NOT NULL,
    subtitle      TEXT NOT NULL,
    max_users     INT NOT NULL,
    monthly_price NUMERIC(10,2) NOT NULL,
    features      TEXT[] DEFAULT '{}',
    feature_labels JSONB DEFAULT '[]'
);

-- Seed default plans (upsert)
INSERT INTO plans (plan, label, subtitle, max_users, monthly_price, features, feature_labels)
VALUES
  ('basic', 'Basic', 'Everything you need to get started', 5, 29,
   ARRAY['Leads','Contacts','Accounts','Deals','Tasks'],
   '[{"label":"Up to 5 users","included":true},{"label":"Leads & Contacts","included":true},{"label":"Deals pipeline","included":true},{"label":"Basic reporting","included":true},{"label":"Email campaigns","included":false},{"label":"Advanced analytics","included":false},{"label":"Custom integrations","included":false}]'::jsonb),
  ('pro', 'Pro', 'Advanced features for growing teams', 25, 79,
   ARRAY['Leads','Contacts','Accounts','Deals','Tasks','Campaigns','Invoices','Quotes'],
   '[{"label":"Up to 25 users","included":true},{"label":"Leads & Contacts","included":true},{"label":"Deals pipeline","included":true},{"label":"Advanced reporting","included":true},{"label":"Email campaigns","included":true},{"label":"Advanced analytics","included":true},{"label":"Custom integrations","included":false}]'::jsonb),
  ('enterprise', 'Enterprise', 'Unlimited scale for large organisations', 999, 199,
   ARRAY['Leads','Contacts','Accounts','Deals','Tasks','Campaigns','Invoices','Quotes','Orders','Products'],
   '[{"label":"Unlimited users","included":true},{"label":"Leads & Contacts","included":true},{"label":"Deals pipeline","included":true},{"label":"Advanced reporting","included":true},{"label":"Email campaigns","included":true},{"label":"Advanced analytics","included":true},{"label":"Custom integrations","included":true}]'::jsonb)
ON CONFLICT (plan) DO NOTHING;

-- -----------------------------------------------------------
-- PASSWORD RESET TOKENS
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id         TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used       BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed a default demo tenant + admin user (password: Admin123!)
INSERT INTO tenants (id, name, domain, plan, status)
VALUES ('demo-tenant-001', 'Demo Corp', 'demo.example.com', 'pro', 'active')
ON CONFLICT (id) DO NOTHING;

INSERT INTO subscriptions (tenant_id, plan, status, max_users, expiry_date, features)
VALUES ('demo-tenant-001', 'pro', 'active', 25, NOW() + INTERVAL '1 year',
        ARRAY['leads','contacts','accounts','deals','tasks','campaigns','invoices','quotes'])
ON CONFLICT DO NOTHING;

-- Password hash below is for 'Admin123!' via bcrypt (generated separately — update via /auth/admin-reset-password if needed)
INSERT INTO users (id, tenant_id, name, email, password_hash, role, status)
VALUES (
  'demo-user-001',
  'demo-tenant-001',
  'Admin User',
  'admin@demo.com',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCMRasHz7fREtF.BjYN7Nqm',
  'ADMIN',
  'active'
)
ON CONFLICT (id) DO NOTHING;
