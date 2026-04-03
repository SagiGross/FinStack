-- ============================================================================
-- CFO FINANCIAL MODEL — POSTGRESQL SCHEMA
-- Multi-tenant SaaS database for P&L, Cashflow, and Scenario Planning
-- ============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. TENANTS (Multi-tenancy)
-- ============================================================================
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    fiscal_year_start SMALLINT NOT NULL DEFAULT 1,  -- 1=Jan, 4=Apr, etc.
    employer_cost_factor NUMERIC(5,4) NOT NULL DEFAULT 1.3500,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 2. DEPARTMENTS
-- ============================================================================
CREATE TYPE dept_enum AS ENUM ('R&D', 'S&M', 'G&A', 'Training');

CREATE TABLE departments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            dept_enum NOT NULL,
    UNIQUE (tenant_id, name)
);

-- ============================================================================
-- 3. EMPLOYEES
-- ============================================================================
CREATE TABLE employees (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    full_name       VARCHAR(255) NOT NULL,
    department      dept_enum NOT NULL,
    monthly_gross   NUMERIC(12,2) NOT NULL,
    hire_date       DATE NOT NULL,
    termination_date DATE,
    is_ghost        BOOLEAN NOT NULL DEFAULT FALSE,  -- for hiring simulations
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_employees_tenant ON employees(tenant_id);
CREATE INDEX idx_employees_dept ON employees(tenant_id, department);

-- ============================================================================
-- 4. CONTRACTS / SALES PIPELINE
-- ============================================================================
CREATE TABLE contracts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_name         VARCHAR(255) NOT NULL,
    country             VARCHAR(100),
    industry            VARCHAR(100),
    year                SMALLINT NOT NULL,
    signing_month       SMALLINT NOT NULL CHECK (signing_month BETWEEN 1 AND 12),
    signing_date        DATE NOT NULL,
    expected_units      NUMERIC(10,2) NOT NULL DEFAULT 0,
    avg_selling_price   NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_value         NUMERIC(14,2) NOT NULL,
    payment_terms_days  INTEGER NOT NULL DEFAULT 30,  -- DSO
    payment_month       VARCHAR(7),                    -- 'MM-YYYY' format
    is_monthly          BOOLEAN NOT NULL DEFAULT FALSE,
    chance              NUMERIC(5,4),                  -- NULL = unweighted
    actual_payment      NUMERIC(14,2),
    actual_payment_month DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contracts_tenant ON contracts(tenant_id);
CREATE INDEX idx_contracts_client ON contracts(tenant_id, client_name);
CREATE INDEX idx_contracts_signing ON contracts(tenant_id, signing_date);

-- ============================================================================
-- 5. EXPENSES
-- ============================================================================
CREATE TABLE expense_categories (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,  -- 'Cloud Services', 'Office Rent', etc.
    UNIQUE (tenant_id, name)
);

CREATE TABLE expenses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    department      dept_enum NOT NULL,
    vendor_name     VARCHAR(255) NOT NULL,
    sub_category    VARCHAR(100) NOT NULL,
    is_cogs         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE expense_monthly (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    expense_id      UUID NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
    month           DATE NOT NULL,              -- first of month
    amount          NUMERIC(14,2) NOT NULL,
    UNIQUE (expense_id, month)
);

CREATE INDEX idx_expenses_tenant ON expenses(tenant_id);
CREATE INDEX idx_expense_monthly_expense ON expense_monthly(expense_id);
CREATE INDEX idx_expense_monthly_month ON expense_monthly(month);

-- ============================================================================
-- 6. SCENARIO PLANNING
-- ============================================================================
CREATE TABLE scenarios (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                    VARCHAR(255) NOT NULL DEFAULT 'Base Case',
    sales_delay_days        INTEGER NOT NULL DEFAULT 0,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ghost employees attached to a scenario
CREATE TABLE scenario_ghost_employees (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scenario_id     UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    full_name       VARCHAR(255) NOT NULL,
    department      dept_enum NOT NULL,
    monthly_gross   NUMERIC(12,2) NOT NULL,
    start_date      DATE NOT NULL,
    termination_date DATE
);

-- Pipeline probability overrides per scenario
CREATE TABLE scenario_pipeline_overrides (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scenario_id     UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    contract_id     UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    override_chance NUMERIC(5,4) NOT NULL,
    UNIQUE (scenario_id, contract_id)
);

-- ============================================================================
-- 7. MATERIALIZED VIEW: Monthly P&L Summary (for dashboard speed)
-- ============================================================================
CREATE MATERIALIZED VIEW mv_monthly_summary AS
SELECT
    e.tenant_id,
    em.month,
    SUM(CASE WHEN e.is_cogs THEN em.amount ELSE 0 END) AS total_cogs,
    SUM(CASE WHEN NOT e.is_cogs AND e.department = 'R&D' THEN em.amount ELSE 0 END) AS opex_rd,
    SUM(CASE WHEN NOT e.is_cogs AND e.department = 'S&M' THEN em.amount ELSE 0 END) AS opex_sm,
    SUM(CASE WHEN NOT e.is_cogs AND e.department = 'G&A' THEN em.amount ELSE 0 END) AS opex_ga,
    SUM(CASE WHEN NOT e.is_cogs AND e.department = 'Training' THEN em.amount ELSE 0 END) AS opex_training,
    SUM(em.amount) AS total_expenses
FROM expenses e
JOIN expense_monthly em ON em.expense_id = e.id
GROUP BY e.tenant_id, em.month;

CREATE UNIQUE INDEX idx_mv_monthly_summary ON mv_monthly_summary(tenant_id, month);

-- ============================================================================
-- 8. SEED DATA — From the uploaded Excel
-- ============================================================================

-- Tenant
INSERT INTO tenants (id, name, currency, employer_cost_factor)
VALUES ('a0000000-0000-0000-0000-000000000001', 'CyberCo', 'USD', 1.3500);

-- Departments
INSERT INTO departments (tenant_id, name) VALUES
('a0000000-0000-0000-0000-000000000001', 'R&D'),
('a0000000-0000-0000-0000-000000000001', 'S&M'),
('a0000000-0000-0000-0000-000000000001', 'G&A'),
('a0000000-0000-0000-0000-000000000001', 'Training');

-- Employees (from Employees_Raw)
INSERT INTO employees (tenant_id, full_name, department, monthly_gross, hire_date) VALUES
('a0000000-0000-0000-0000-000000000001', 'Etti Berger',       'G&A', 16487.46, '2024-01-01'),
('a0000000-0000-0000-0000-000000000001', 'Shai Grumet',       'R&D', 11314.92, '2024-01-01'),
('a0000000-0000-0000-0000-000000000001', 'Arye Laskin',       'R&D',  9051.94, '2024-01-01'),
('a0000000-0000-0000-0000-000000000001', 'Oren Chappo',       'R&D', 11961.49, '2024-01-01'),
('a0000000-0000-0000-0000-000000000001', 'Eduardo Borotchin', 'S&M', 10345.07, '2024-01-01'),
('a0000000-0000-0000-0000-000000000001', 'Nitai Driel',       'R&D',   387.94, '2024-01-01'),
('a0000000-0000-0000-0000-000000000001', 'Elad Lev',          'S&M',  8082.09, '2024-01-01'),
('a0000000-0000-0000-0000-000000000001', 'Tiki Tavero',       'S&M',  6465.67, '2024-01-01'),
('a0000000-0000-0000-0000-000000000001', 'Meirav Zetz',       'G&A',  2020.52, '2024-01-01');

INSERT INTO employees (tenant_id, full_name, department, monthly_gross, hire_date, termination_date) VALUES
('a0000000-0000-0000-0000-000000000001', 'Yaniv Barkai',  'R&D', 19431.60, '2024-01-01', '2026-01-31'),
('a0000000-0000-0000-0000-000000000001', 'Elad Sheskin',  'R&D',     0.00, '2024-01-01', '2025-12-31');

-- Base scenario
INSERT INTO scenarios (tenant_id, name, sales_delay_days)
VALUES ('a0000000-0000-0000-0000-000000000001', 'Base Case', 0);
