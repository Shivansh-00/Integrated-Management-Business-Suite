-- ===================================================================
-- IBMS Enterprise — Supabase PostgreSQL Schema
-- ===================================================================
-- Run this in Supabase SQL Editor to create all tables.
-- Replaces both MongoDB collections and MariaDB tables.
-- ===================================================================

-- Enable UUID extension (already enabled in Supabase by default)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===================================================================
-- AUTH / SYSTEM TABLES (formerly MongoDB collections)
-- ===================================================================

-- Users
CREATE TABLE IF NOT EXISTS users (
    id            UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id       TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'viewer',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified   BOOLEAN NOT NULL DEFAULT FALSE,
    totp_secret   TEXT,
    totp_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TEXT NOT NULL,
    last_login    TEXT,
    failed_attempts INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    audit_id    TEXT UNIQUE NOT NULL,
    event_type  TEXT NOT NULL,
    user_id     TEXT NOT NULL DEFAULT '',
    ip          TEXT NOT NULL DEFAULT '',
    timestamp   TEXT NOT NULL,
    details     JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);

-- Refresh Tokens
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    token       TEXT UNIQUE NOT NULL,
    user_id     TEXT NOT NULL,
    device_fp   TEXT NOT NULL DEFAULT '',
    issued_at   INTEGER NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    family      TEXT NOT NULL,
    revoked     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_refresh_token ON refresh_tokens(token);
CREATE INDEX IF NOT EXISTS idx_refresh_user ON refresh_tokens(user_id);

-- Rate Limits
CREATE TABLE IF NOT EXISTS rate_limits (
    id            UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    key           TEXT UNIQUE NOT NULL,
    attempts      INTEGER NOT NULL DEFAULT 0,
    first_attempt DOUBLE PRECISION NOT NULL DEFAULT 0,
    locked_until  DOUBLE PRECISION NOT NULL DEFAULT 0
);

-- CSRF Tokens
CREATE TABLE IF NOT EXISTS csrf_tokens (
    id         UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    token      TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_csrf_token ON csrf_tokens(token);

-- KPI Snapshots
CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id           UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    snapshot_id  TEXT UNIQUE NOT NULL,
    company      TEXT NOT NULL,
    recorded_at  TEXT NOT NULL,
    data         JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_kpi_company_time ON kpi_snapshots(company, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_recorded ON kpi_snapshots(recorded_at DESC);

-- KPI Latest (one row per company for fast dashboard reads)
CREATE TABLE IF NOT EXISTS kpi_latest (
    id      UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    company TEXT UNIQUE NOT NULL,
    data    JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- AI Recommendations
CREATE TABLE IF NOT EXISTS ai_recommendations (
    id                  UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    rec_id              TEXT UNIQUE NOT NULL,
    company             TEXT NOT NULL,
    context_type        TEXT NOT NULL,
    recommendation_code TEXT NOT NULL,
    confidence          DOUBLE PRECISION NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'Open',
    payload             JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_airec_company ON ai_recommendations(company, status, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_airec_context ON ai_recommendations(context_type);

-- Enterprise Profiles
CREATE TABLE IF NOT EXISTS enterprise_profiles (
    id      UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    data    JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Webhook Logs
CREATE TABLE IF NOT EXISTS webhook_logs (
    id            UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    log_id        TEXT UNIQUE NOT NULL,
    provider      TEXT NOT NULL,
    event_type    TEXT NOT NULL,
    signature     TEXT NOT NULL DEFAULT '',
    request_body  TEXT NOT NULL DEFAULT '',
    processed     BOOLEAN NOT NULL DEFAULT FALSE,
    http_status   INTEGER NOT NULL DEFAULT 200,
    response_body TEXT NOT NULL DEFAULT '',
    received_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_webhook_processed ON webhook_logs(processed, received_at);

-- Smart Decision Rules
CREATE TABLE IF NOT EXISTS smart_decision_rules (
    id         UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    rule_id    TEXT UNIQUE NOT NULL,
    rule_name  TEXT NOT NULL,
    module     TEXT NOT NULL,
    threshold  DOUBLE PRECISION NOT NULL DEFAULT 50.0,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_rules_enabled ON smart_decision_rules(is_enabled, module);

-- AI Alerts
CREATE TABLE IF NOT EXISTS ai_alerts (
    id                 UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    alert_id           TEXT UNIQUE NOT NULL,
    title              TEXT NOT NULL,
    severity           TEXT NOT NULL,
    reference_doctype  TEXT NOT NULL DEFAULT '',
    reference_name     TEXT NOT NULL DEFAULT '',
    status             TEXT NOT NULL DEFAULT 'Open',
    risk_score         DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alerts_status ON ai_alerts(status, created_at DESC);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    notif_id    TEXT UNIQUE NOT NULL,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    level       TEXT NOT NULL DEFAULT 'info',
    target_user TEXT NOT NULL DEFAULT '',
    read        BOOLEAN NOT NULL DEFAULT FALSE,
    timestamp   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(target_user, timestamp DESC);

-- ===================================================================
-- ERP TABLES (formerly MariaDB)
-- ===================================================================

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    email               TEXT UNIQUE,
    phone               TEXT NOT NULL DEFAULT '',
    company             TEXT NOT NULL DEFAULT '',
    address             TEXT NOT NULL DEFAULT '',
    city                TEXT NOT NULL DEFAULT '',
    state               TEXT NOT NULL DEFAULT '',
    country             TEXT NOT NULL DEFAULT '',
    segment             TEXT NOT NULL DEFAULT 'small_business',
    credit_limit        NUMERIC(15,2) NOT NULL DEFAULT 50000.00,
    outstanding_balance NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_segment ON customers(segment);
CREATE INDEX IF NOT EXISTS idx_customers_active ON customers(is_active);

-- Products
CREATE TABLE IF NOT EXISTS products (
    id              TEXT PRIMARY KEY,
    sku             TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT '',
    unit_price      NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    cost_price      NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    tax_rate        NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    stock_quantity  INTEGER NOT NULL DEFAULT 0,
    reorder_level   INTEGER NOT NULL DEFAULT 10,
    unit            TEXT NOT NULL DEFAULT 'unit',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id              TEXT PRIMARY KEY,
    order_number    TEXT UNIQUE NOT NULL,
    customer_id     TEXT NOT NULL REFERENCES customers(id),
    order_date      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          TEXT NOT NULL DEFAULT 'draft',
    subtotal        NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    tax_amount      NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    discount_amount NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    total_amount    NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Order Items
CREATE TABLE IF NOT EXISTS order_items (
    id           TEXT PRIMARY KEY,
    order_id     TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id   TEXT NOT NULL REFERENCES products(id),
    quantity     INTEGER NOT NULL DEFAULT 1,
    unit_price   NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    discount_pct NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    line_total   NUMERIC(15,2) NOT NULL DEFAULT 0.00
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id              TEXT PRIMARY KEY,
    invoice_number  TEXT UNIQUE NOT NULL,
    customer_id     TEXT NOT NULL REFERENCES customers(id),
    order_id        TEXT REFERENCES orders(id),
    invoice_date    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_date        TEXT,
    status          TEXT NOT NULL DEFAULT 'draft',
    subtotal        NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    tax_amount      NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    total_amount    NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    paid_amount     NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);

-- Inventory Movements
CREATE TABLE IF NOT EXISTS inventory_movements (
    id              TEXT PRIMARY KEY,
    product_id      TEXT NOT NULL REFERENCES products(id),
    movement_type   TEXT NOT NULL,
    quantity        INTEGER NOT NULL,
    reference_type  TEXT,
    reference_id    TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory_movements(product_id);

-- Employees
CREATE TABLE IF NOT EXISTS employees (
    id              TEXT PRIMARY KEY,
    employee_code   TEXT UNIQUE NOT NULL,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    phone           TEXT NOT NULL DEFAULT '',
    department      TEXT NOT NULL DEFAULT '',
    designation     TEXT NOT NULL DEFAULT '',
    date_of_joining TEXT,
    salary          NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_employees_dept ON employees(department);
CREATE INDEX IF NOT EXISTS idx_employees_active ON employees(is_active);
