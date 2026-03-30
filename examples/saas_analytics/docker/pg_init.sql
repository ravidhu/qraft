-- Seed data for saas_analytics example
-- Source: three SaaS application databases (PostgreSQL)

-- ════════════════════════════════════════
-- CRM source (Salesforce-like)
-- ════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS crm_raw;

CREATE TABLE crm_raw.accounts (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    industry     TEXT NOT NULL,
    company_size TEXT NOT NULL,
    country      TEXT NOT NULL,
    created_at   TIMESTAMP NOT NULL
);
INSERT INTO crm_raw.accounts (id, name, industry, company_size, country, created_at) VALUES
    ('ACC-001', 'Acme Corp',        'Technology',     'mid-market',  'US', '2023-01-15 10:00:00'),
    ('ACC-002', 'Globex Inc',       'Finance',        'enterprise',  'UK', '2023-03-20 14:30:00'),
    ('ACC-003', 'Initech',          'Technology',     'startup',     'US', '2023-06-01 09:00:00'),
    ('ACC-004', 'Stark Industries', 'Manufacturing',  'enterprise',  'US', '2023-08-10 11:00:00'),
    ('ACC-005', 'Wayne Enterprises','Finance',        'enterprise',  'US', '2023-10-05 16:00:00'),
    ('ACC-006', 'Pied Piper',       'Technology',     'startup',     'US', '2024-01-12 08:00:00'),
    ('ACC-007', 'Hooli',            'Technology',     'enterprise',  'US', '2024-02-28 13:00:00'),
    ('ACC-008', 'Cyberdyne',        'Manufacturing',  'mid-market',  'DE', '2024-04-15 10:00:00');

CREATE TABLE crm_raw.contacts (
    id         TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES crm_raw.accounts(id),
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    role       TEXT NOT NULL
);
INSERT INTO crm_raw.contacts (id, account_id, name, email, role) VALUES
    ('CON-001', 'ACC-001', 'John Smith',        'john@acme.com',          'CTO'),
    ('CON-002', 'ACC-001', 'Jane Doe',          'jane@acme.com',          'VP Engineering'),
    ('CON-003', 'ACC-002', 'Bob Wilson',         'bob@globex.com',        'CFO'),
    ('CON-004', 'ACC-003', 'Alice Brown',        'alice@initech.com',     'CEO'),
    ('CON-005', 'ACC-004', 'Tony Stark',         'tony@stark.com',        'CEO'),
    ('CON-006', 'ACC-005', 'Bruce Wayne',        'bruce@wayne.com',       'CEO'),
    ('CON-007', 'ACC-006', 'Richard Hendricks',  'richard@piedpiper.com', 'CEO'),
    ('CON-008', 'ACC-007', 'Gavin Belson',       'gavin@hooli.com',       'CEO'),
    ('CON-009', 'ACC-008', 'Miles Dyson',        'miles@cyberdyne.com',   'CTO');

CREATE TABLE crm_raw.opportunities (
    id         TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES crm_raw.accounts(id),
    stage      TEXT NOT NULL,
    amount     DECIMAL(12,2) NOT NULL,
    close_date DATE NOT NULL
);
INSERT INTO crm_raw.opportunities (id, account_id, stage, amount, close_date) VALUES
    ('OPP-001', 'ACC-001', 'closed_won',  50000,  '2023-03-01'),
    ('OPP-002', 'ACC-002', 'closed_won',  120000, '2023-05-15'),
    ('OPP-003', 'ACC-003', 'closed_won',  15000,  '2023-07-20'),
    ('OPP-004', 'ACC-004', 'closed_won',  200000, '2023-09-30'),
    ('OPP-005', 'ACC-005', 'closed_won',  180000, '2023-11-15'),
    ('OPP-006', 'ACC-006', 'closed_won',  8000,   '2024-02-01'),
    ('OPP-007', 'ACC-007', 'closed_won',  300000, '2024-04-01'),
    ('OPP-008', 'ACC-001', 'negotiation', 75000,  '2024-06-15'),
    ('OPP-009', 'ACC-008', 'closed_won',  45000,  '2024-05-20'),
    ('OPP-010', 'ACC-003', 'closed_lost', 25000,  '2024-03-10');

-- ════════════════════════════════════════
-- Billing source (Stripe-like)
-- ════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS billing_raw;

CREATE TABLE billing_raw.subscriptions (
    id           TEXT PRIMARY KEY,
    account_id   TEXT NOT NULL,
    plan         TEXT NOT NULL,
    mrr          DECIMAL(10,2) NOT NULL,
    status       TEXT NOT NULL,
    started_at   DATE NOT NULL,
    cancelled_at DATE
);
INSERT INTO billing_raw.subscriptions (id, account_id, plan, mrr, status, started_at, cancelled_at) VALUES
    ('SUB-001', 'ACC-001', 'professional', 4500.00,  'active',    '2023-03-01', NULL),
    ('SUB-002', 'ACC-002', 'enterprise',   12000.00, 'active',    '2023-05-15', NULL),
    ('SUB-003', 'ACC-003', 'starter',      1200.00,  'cancelled', '2023-07-20', '2024-01-20'),
    ('SUB-004', 'ACC-004', 'enterprise',   18000.00, 'active',    '2023-09-30', NULL),
    ('SUB-005', 'ACC-005', 'enterprise',   15000.00, 'active',    '2023-11-15', NULL),
    ('SUB-006', 'ACC-006', 'starter',      800.00,   'active',    '2024-02-01', NULL),
    ('SUB-007', 'ACC-007', 'enterprise',   25000.00, 'active',    '2024-04-01', NULL),
    ('SUB-008', 'ACC-008', 'professional', 3500.00,  'active',    '2024-05-20', NULL);

CREATE TABLE billing_raw.invoices (
    id              TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES billing_raw.subscriptions(id),
    amount          DECIMAL(10,2) NOT NULL,
    status          TEXT NOT NULL,
    issued_at       DATE NOT NULL,
    paid_at         DATE
);
INSERT INTO billing_raw.invoices (id, subscription_id, amount, status, issued_at, paid_at) VALUES
    ('INV-001', 'SUB-001', 4500.00,  'paid',    '2024-01-01', '2024-01-05'),
    ('INV-002', 'SUB-001', 4500.00,  'paid',    '2024-02-01', '2024-02-03'),
    ('INV-003', 'SUB-002', 12000.00, 'paid',    '2024-01-01', '2024-01-02'),
    ('INV-004', 'SUB-002', 12000.00, 'paid',    '2024-02-01', '2024-02-04'),
    ('INV-005', 'SUB-004', 18000.00, 'paid',    '2024-01-01', '2024-01-03'),
    ('INV-006', 'SUB-005', 15000.00, 'paid',    '2024-01-01', '2024-01-10'),
    ('INV-007', 'SUB-006', 800.00,   'paid',    '2024-03-01', '2024-03-05'),
    ('INV-008', 'SUB-007', 25000.00, 'paid',    '2024-05-01', '2024-05-02'),
    ('INV-009', 'SUB-008', 3500.00,  'paid',    '2024-06-01', '2024-06-08'),
    ('INV-010', 'SUB-005', 15000.00, 'overdue', '2024-02-01', NULL);

CREATE TABLE billing_raw.payments (
    id         TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL REFERENCES billing_raw.invoices(id),
    amount     DECIMAL(10,2) NOT NULL,
    method     TEXT NOT NULL,
    paid_at    TIMESTAMP NOT NULL
);
INSERT INTO billing_raw.payments (id, invoice_id, amount, method, paid_at) VALUES
    ('PAY-001', 'INV-001', 4500.00,  'credit_card', '2024-01-05 10:00:00'),
    ('PAY-002', 'INV-002', 4500.00,  'credit_card', '2024-02-03 11:00:00'),
    ('PAY-003', 'INV-003', 12000.00, 'wire',        '2024-01-02 09:00:00'),
    ('PAY-004', 'INV-004', 12000.00, 'wire',        '2024-02-04 14:00:00'),
    ('PAY-005', 'INV-005', 18000.00, 'wire',        '2024-01-03 10:00:00'),
    ('PAY-006', 'INV-006', 15000.00, 'wire',        '2024-01-10 16:00:00'),
    ('PAY-007', 'INV-007', 800.00,   'credit_card', '2024-03-05 12:00:00'),
    ('PAY-008', 'INV-008', 25000.00, 'wire',        '2024-05-02 09:00:00'),
    ('PAY-009', 'INV-009', 3500.00,  'credit_card', '2024-06-08 15:00:00');

-- ════════════════════════════════════════
-- Product source (telemetry)
-- ════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS product_raw;

CREATE TABLE product_raw.users (
    id             TEXT PRIMARY KEY,
    account_id     TEXT NOT NULL,
    email          TEXT NOT NULL,
    role           TEXT NOT NULL,
    created_at     TIMESTAMP NOT NULL,
    last_active_at TIMESTAMP
);
INSERT INTO product_raw.users (id, account_id, email, role, created_at, last_active_at) VALUES
    ('USR-001', 'ACC-001', 'john@acme.com',         'admin',  '2023-03-02 10:00:00', '2024-06-15 09:00:00'),
    ('USR-002', 'ACC-001', 'jane@acme.com',         'member', '2023-03-05 11:00:00', '2024-06-14 16:00:00'),
    ('USR-003', 'ACC-002', 'bob@globex.com',        'admin',  '2023-05-16 09:00:00', '2024-06-15 14:00:00'),
    ('USR-004', 'ACC-003', 'alice@initech.com',     'admin',  '2023-07-21 10:00:00', '2023-12-15 11:00:00'),
    ('USR-005', 'ACC-004', 'tony@stark.com',        'admin',  '2023-10-01 08:00:00', '2024-06-15 10:00:00'),
    ('USR-006', 'ACC-005', 'bruce@wayne.com',       'admin',  '2023-11-16 09:00:00', '2024-06-14 22:00:00'),
    ('USR-007', 'ACC-006', 'richard@piedpiper.com', 'admin',  '2024-02-02 08:00:00', '2024-06-15 11:00:00'),
    ('USR-008', 'ACC-007', 'gavin@hooli.com',       'admin',  '2024-04-02 10:00:00', '2024-06-15 13:00:00'),
    ('USR-009', 'ACC-008', 'miles@cyberdyne.com',   'admin',  '2024-05-21 09:00:00', '2024-06-10 15:00:00'),
    ('USR-010', 'ACC-001', 'dev1@acme.com',         'member', '2023-06-01 10:00:00', '2024-06-15 17:00:00'),
    ('USR-011', 'ACC-004', 'dev1@stark.com',        'member', '2024-01-10 09:00:00', '2024-06-15 12:00:00'),
    ('USR-012', 'ACC-007', 'dev1@hooli.com',        'member', '2024-04-05 10:00:00', '2024-06-14 18:00:00');

CREATE TABLE product_raw.events (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES product_raw.users(id),
    event_type TEXT NOT NULL,
    event_ts   TIMESTAMP NOT NULL
);
INSERT INTO product_raw.events (id, user_id, event_type, event_ts) VALUES
    ('EVT-001', 'USR-001', 'login',          '2024-06-15 09:00:00'),
    ('EVT-002', 'USR-001', 'dashboard_view', '2024-06-15 09:05:00'),
    ('EVT-003', 'USR-002', 'login',          '2024-06-14 16:00:00'),
    ('EVT-004', 'USR-003', 'login',          '2024-06-15 14:00:00'),
    ('EVT-005', 'USR-003', 'report_export',  '2024-06-15 14:30:00'),
    ('EVT-006', 'USR-005', 'login',          '2024-06-15 10:00:00'),
    ('EVT-007', 'USR-005', 'api_call',       '2024-06-15 10:15:00'),
    ('EVT-008', 'USR-006', 'login',          '2024-06-14 22:00:00'),
    ('EVT-009', 'USR-007', 'login',          '2024-06-15 11:00:00'),
    ('EVT-010', 'USR-008', 'login',          '2024-06-15 13:00:00'),
    ('EVT-011', 'USR-010', 'login',          '2024-06-15 17:00:00'),
    ('EVT-012', 'USR-010', 'dashboard_view', '2024-06-15 17:10:00'),
    ('EVT-013', 'USR-011', 'login',          '2024-06-15 12:00:00'),
    ('EVT-014', 'USR-012', 'login',          '2024-06-14 18:00:00');

CREATE TABLE product_raw.feature_usage (
    user_id     TEXT NOT NULL REFERENCES product_raw.users(id),
    feature     TEXT NOT NULL,
    usage_count INTEGER NOT NULL,
    period      DATE NOT NULL,
    PRIMARY KEY (user_id, feature, period)
);
INSERT INTO product_raw.feature_usage (user_id, feature, usage_count, period) VALUES
    ('USR-001', 'dashboards', 45,   '2024-06-01'),
    ('USR-001', 'reports',    12,   '2024-06-01'),
    ('USR-001', 'api',        200,  '2024-06-01'),
    ('USR-002', 'dashboards', 30,   '2024-06-01'),
    ('USR-003', 'dashboards', 60,   '2024-06-01'),
    ('USR-003', 'reports',    25,   '2024-06-01'),
    ('USR-003', 'api',        500,  '2024-06-01'),
    ('USR-005', 'api',        1500, '2024-06-01'),
    ('USR-005', 'dashboards', 20,   '2024-06-01'),
    ('USR-006', 'dashboards', 55,   '2024-06-01'),
    ('USR-006', 'reports',    18,   '2024-06-01'),
    ('USR-007', 'dashboards', 10,   '2024-06-01'),
    ('USR-008', 'api',        2000, '2024-06-01'),
    ('USR-008', 'dashboards', 35,   '2024-06-01'),
    ('USR-010', 'dashboards', 22,   '2024-06-01'),
    ('USR-011', 'api',        300,  '2024-06-01'),
    ('USR-012', 'dashboards', 15,   '2024-06-01');
