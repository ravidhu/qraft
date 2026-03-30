-- Seed data for saas_analytics example
-- Source: SaaS application databases (PostgreSQL)
-- Three schemas representing CRM, billing, and product telemetry systems

-- ─────────────────────────────────────────────
-- CRM source
-- ─────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS crm_raw;

CREATE TABLE crm_raw.accounts (
    account_id     INTEGER PRIMARY KEY,
    account_name   VARCHAR(100) NOT NULL,
    industry       VARCHAR(50)  NOT NULL,
    company_size   VARCHAR(20)  NOT NULL,
    country        VARCHAR(50)  NOT NULL,
    created_at     DATE         NOT NULL
);

INSERT INTO crm_raw.accounts VALUES
    (1,  'Acme Corp',        'Technology',    'enterprise', 'USA',       '2022-01-10'),
    (2,  'GlobalTech',       'Technology',    'mid_market', 'UK',        '2022-03-15'),
    (3,  'DataFlow Inc',     'Analytics',     'startup',    'Germany',   '2022-06-20'),
    (4,  'RetailMax',        'Retail',        'enterprise', 'France',    '2022-08-05'),
    (5,  'HealthFirst',      'Healthcare',    'mid_market', 'Canada',    '2022-10-12'),
    (6,  'EduLearn',         'Education',     'startup',    'Australia', '2023-01-08'),
    (7,  'FinServe',         'Finance',       'enterprise', 'USA',       '2023-03-20'),
    (8,  'CloudOps',         'Technology',    'mid_market', 'India',     '2023-05-15'),
    (9,  'MediaPulse',       'Media',         'startup',    'Brazil',    '2023-07-22'),
    (10, 'BuildRight',       'Construction',  'mid_market', 'Japan',     '2023-09-10'),
    (11, 'GreenEnergy Co',   'Energy',        'enterprise', 'Norway',    '2023-11-01'),
    (12, 'SmartLogistics',   'Logistics',     'startup',    'Singapore', '2024-01-15');

CREATE TABLE crm_raw.contacts (
    contact_id   INTEGER PRIMARY KEY,
    account_id   INTEGER NOT NULL,
    name         VARCHAR(100) NOT NULL,
    role         VARCHAR(50)  NOT NULL,
    email        VARCHAR(150) NOT NULL
);

INSERT INTO crm_raw.contacts VALUES
    (1,  1,  'John Smith',       'CTO',               'john@acme.com'),
    (2,  1,  'Lisa Park',        'VP Engineering',    'lisa@acme.com'),
    (3,  2,  'Mark Brown',       'Data Lead',         'mark@globaltech.com'),
    (4,  3,  'Sarah Lee',        'CEO',               'sarah@dataflow.io'),
    (5,  4,  'Pierre Dupont',    'IT Director',       'pierre@retailmax.fr'),
    (6,  5,  'Amy Chen',         'Head of Analytics', 'amy@healthfirst.ca'),
    (7,  6,  'Tom Wilson',       'Founder',           'tom@edulearn.com.au'),
    (8,  7,  'Rachel Green',     'CIO',               'rachel@finserve.com'),
    (9,  8,  'Raj Patel',        'Tech Lead',         'raj@cloudops.in'),
    (10, 9,  'Ana Costa',        'Product Manager',   'ana@mediapulse.br'),
    (11, 10, 'Yuki Tanaka',      'IT Manager',        'yuki@buildright.jp'),
    (12, 11, 'Erik Larsen',      'VP Operations',     'erik@greenenergy.no'),
    (13, 12, 'Wei Lin',          'CTO',               'wei@smartlogistics.sg'),
    (14, 1,  'David Kim',        'Engineering Lead',  'david@acme.com'),
    (15, 7,  'Michael Ross',     'VP Data',           'michael@finserve.com');

CREATE TABLE crm_raw.opportunities (
    opportunity_id INTEGER PRIMARY KEY,
    account_id     INTEGER NOT NULL,
    deal_amount    DECIMAL(12,2) NOT NULL,
    stage          VARCHAR(30)   NOT NULL,
    created_at     DATE          NOT NULL,
    closed_at      DATE
);

INSERT INTO crm_raw.opportunities VALUES
    (1,  1,  150000.00, 'closed_won',  '2022-02-01', '2022-04-15'),
    (2,  2,   45000.00, 'closed_won',  '2022-04-10', '2022-06-20'),
    (3,  3,   12000.00, 'closed_won',  '2022-07-01', '2022-08-15'),
    (4,  4,  200000.00, 'closed_won',  '2022-09-01', '2022-11-30'),
    (5,  5,   60000.00, 'closed_won',  '2022-11-15', '2023-01-20'),
    (6,  6,    8000.00, 'closed_lost', '2023-02-01', '2023-03-15'),
    (7,  7,  300000.00, 'closed_won',  '2023-04-01', '2023-06-30'),
    (8,  8,   35000.00, 'closed_won',  '2023-06-01', '2023-08-10'),
    (9,  9,   15000.00, 'negotiation', '2023-08-15',  NULL),
    (10, 10,  50000.00, 'closed_won',  '2023-10-01', '2023-12-15'),
    (11, 11, 180000.00, 'proposal',    '2023-12-01',  NULL),
    (12, 12,  20000.00, 'closed_lost', '2024-01-20', '2024-02-28'),
    (13, 1,  175000.00, 'closed_won',  '2023-06-01', '2023-09-15'),
    (14, 4,  220000.00, 'negotiation', '2024-01-10',  NULL);

-- ─────────────────────────────────────────────
-- Billing source
-- ─────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS billing_raw;

CREATE TABLE billing_raw.subscriptions (
    subscription_id INTEGER PRIMARY KEY,
    account_id      INTEGER     NOT NULL,
    plan_name       VARCHAR(30) NOT NULL,
    mrr             DECIMAL(10,2) NOT NULL,
    status          VARCHAR(20) NOT NULL,
    started_at      DATE        NOT NULL,
    cancelled_at    DATE
);

INSERT INTO billing_raw.subscriptions VALUES
    (1,  1,  'enterprise', 12500.00, 'active',    '2022-04-15', NULL),
    (2,  2,  'business',    3750.00, 'active',    '2022-06-20', NULL),
    (3,  3,  'starter',     1000.00, 'active',    '2022-08-15', NULL),
    (4,  4,  'enterprise', 16666.00, 'active',    '2022-11-30', NULL),
    (5,  5,  'business',    5000.00, 'active',    '2023-01-20', NULL),
    (6,  6,  'starter',      666.00, 'cancelled', '2023-03-15', '2023-09-15'),
    (7,  7,  'enterprise', 25000.00, 'active',    '2023-06-30', NULL),
    (8,  8,  'business',    2916.00, 'active',    '2023-08-10', NULL),
    (9,  9,  'starter',     1250.00, 'active',    '2023-09-01', NULL),
    (10, 10, 'business',    4166.00, 'active',    '2023-12-15', NULL),
    (11, 11, 'enterprise', 15000.00, 'active',    '2024-01-01', NULL),
    (12, 12, 'starter',      800.00, 'cancelled', '2024-02-01', '2024-05-01');

CREATE TABLE billing_raw.invoices (
    invoice_id  INTEGER PRIMARY KEY,
    account_id  INTEGER       NOT NULL,
    amount      DECIMAL(10,2) NOT NULL,
    status      VARCHAR(20)   NOT NULL,
    issued_at   DATE          NOT NULL,
    paid_at     DATE
);

INSERT INTO billing_raw.invoices VALUES
    (1,  1,  12500.00, 'paid',    '2023-01-01', '2023-01-05'),
    (2,  1,  12500.00, 'paid',    '2023-02-01', '2023-02-03'),
    (3,  2,   3750.00, 'paid',    '2023-01-01', '2023-01-10'),
    (4,  3,   1000.00, 'paid',    '2023-01-01', '2023-01-08'),
    (5,  4,  16666.00, 'paid',    '2023-01-01', '2023-01-02'),
    (6,  5,   5000.00, 'paid',    '2023-02-01', '2023-02-12'),
    (7,  6,    666.00, 'paid',    '2023-04-01', '2023-04-15'),
    (8,  7,  25000.00, 'paid',    '2023-07-01', '2023-07-02'),
    (9,  8,   2916.00, 'paid',    '2023-09-01', '2023-09-05'),
    (10, 9,   1250.00, 'overdue', '2023-10-01',  NULL),
    (11, 10,  4166.00, 'paid',    '2024-01-01', '2024-01-03'),
    (12, 11, 15000.00, 'paid',    '2024-02-01', '2024-02-01'),
    (13, 1,  12500.00, 'paid',    '2023-03-01', '2023-03-04'),
    (14, 4,  16666.00, 'paid',    '2023-02-01', '2023-02-02'),
    (15, 7,  25000.00, 'paid',    '2023-08-01', '2023-08-03');

CREATE TABLE billing_raw.payments (
    payment_id  INTEGER PRIMARY KEY,
    invoice_id  INTEGER       NOT NULL,
    amount      DECIMAL(10,2) NOT NULL,
    method      VARCHAR(30)   NOT NULL,
    paid_at     DATE          NOT NULL
);

INSERT INTO billing_raw.payments VALUES
    (1,  1,  12500.00, 'credit_card',  '2023-01-05'),
    (2,  2,  12500.00, 'credit_card',  '2023-02-03'),
    (3,  3,   3750.00, 'bank_transfer','2023-01-10'),
    (4,  4,   1000.00, 'credit_card',  '2023-01-08'),
    (5,  5,  16666.00, 'bank_transfer','2023-01-02'),
    (6,  6,   5000.00, 'credit_card',  '2023-02-12'),
    (7,  7,    666.00, 'credit_card',  '2023-04-15'),
    (8,  8,  25000.00, 'bank_transfer','2023-07-02'),
    (9,  9,   2916.00, 'credit_card',  '2023-09-05'),
    (10, 11,  4166.00, 'bank_transfer','2024-01-03'),
    (11, 12, 15000.00, 'bank_transfer','2024-02-01'),
    (12, 13, 12500.00, 'credit_card',  '2023-03-04'),
    (13, 14, 16666.00, 'bank_transfer','2023-02-02'),
    (14, 15, 25000.00, 'bank_transfer','2023-08-03');

-- ─────────────────────────────────────────────
-- Product telemetry source
-- ─────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS product_raw;

CREATE TABLE product_raw.users (
    user_id        INTEGER PRIMARY KEY,
    account_id     INTEGER     NOT NULL,
    email          VARCHAR(150) NOT NULL,
    role           VARCHAR(30) NOT NULL,
    last_active_at DATE
);

INSERT INTO product_raw.users VALUES
    (1,  1,  'john@acme.com',          'admin',  '2024-02-28'),
    (2,  1,  'lisa@acme.com',          'user',   '2024-02-27'),
    (3,  1,  'david@acme.com',         'user',   '2024-02-25'),
    (4,  2,  'mark@globaltech.com',    'admin',  '2024-02-28'),
    (5,  2,  'analyst1@globaltech.com','user',   '2024-02-20'),
    (6,  3,  'sarah@dataflow.io',      'admin',  '2024-02-28'),
    (7,  4,  'pierre@retailmax.fr',    'admin',  '2024-02-26'),
    (8,  4,  'analyst@retailmax.fr',   'user',   '2024-02-24'),
    (9,  5,  'amy@healthfirst.ca',     'admin',  '2024-02-28'),
    (10, 5,  'nurse@healthfirst.ca',   'user',   '2024-01-15'),
    (11, 7,  'rachel@finserve.com',    'admin',  '2024-02-28'),
    (12, 7,  'michael@finserve.com',   'user',   '2024-02-27'),
    (13, 7,  'analyst@finserve.com',   'user',   '2024-02-26'),
    (14, 8,  'raj@cloudops.in',        'admin',  '2024-02-15'),
    (15, 10, 'yuki@buildright.jp',     'admin',  '2024-02-28');

CREATE TABLE product_raw.events (
    event_id   INTEGER PRIMARY KEY,
    user_id    INTEGER     NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP   NOT NULL
);

INSERT INTO product_raw.events VALUES
    (1,  1,  'login',           '2024-02-28 09:00:00'),
    (2,  1,  'dashboard_view',  '2024-02-28 09:05:00'),
    (3,  1,  'api_call',        '2024-02-28 09:10:00'),
    (4,  2,  'login',           '2024-02-27 10:00:00'),
    (5,  2,  'report_export',   '2024-02-27 10:30:00'),
    (6,  3,  'login',           '2024-02-25 14:00:00'),
    (7,  4,  'login',           '2024-02-28 08:00:00'),
    (8,  4,  'dashboard_view',  '2024-02-28 08:15:00'),
    (9,  6,  'login',           '2024-02-28 11:00:00'),
    (10, 6,  'api_call',        '2024-02-28 11:20:00'),
    (11, 7,  'login',           '2024-02-26 09:00:00'),
    (12, 7,  'dashboard_view',  '2024-02-26 09:30:00'),
    (13, 9,  'login',           '2024-02-28 07:00:00'),
    (14, 11, 'login',           '2024-02-28 08:30:00'),
    (15, 11, 'api_call',        '2024-02-28 08:45:00'),
    (16, 11, 'dashboard_view',  '2024-02-28 09:00:00'),
    (17, 12, 'login',           '2024-02-27 10:00:00'),
    (18, 12, 'report_export',   '2024-02-27 10:15:00'),
    (19, 13, 'login',           '2024-02-26 13:00:00'),
    (20, 15, 'login',           '2024-02-28 06:00:00');

CREATE TABLE product_raw.feature_usage (
    usage_id    INTEGER PRIMARY KEY,
    user_id     INTEGER     NOT NULL,
    feature     VARCHAR(50) NOT NULL,
    usage_count INTEGER     NOT NULL,
    period      DATE        NOT NULL
);

INSERT INTO product_raw.feature_usage VALUES
    (1,  1,  'api',        250,  '2024-02-01'),
    (2,  1,  'dashboards',  45,  '2024-02-01'),
    (3,  1,  'reports',     12,  '2024-02-01'),
    (4,  2,  'dashboards',  30,  '2024-02-01'),
    (5,  2,  'reports',      8,  '2024-02-01'),
    (6,  3,  'api',         50,  '2024-02-01'),
    (7,  4,  'api',        120,  '2024-02-01'),
    (8,  4,  'dashboards',  25,  '2024-02-01'),
    (9,  5,  'dashboards',  10,  '2024-02-01'),
    (10, 6,  'api',        180,  '2024-02-01'),
    (11, 6,  'dashboards',  35,  '2024-02-01'),
    (12, 7,  'dashboards',  15,  '2024-02-01'),
    (13, 8,  'dashboards',   5,  '2024-02-01'),
    (14, 9,  'api',         80,  '2024-02-01'),
    (15, 9,  'reports',      3,  '2024-02-01'),
    (16, 11, 'api',        300,  '2024-02-01'),
    (17, 11, 'dashboards',  60,  '2024-02-01'),
    (18, 11, 'reports',     20,  '2024-02-01'),
    (19, 12, 'dashboards',  40,  '2024-02-01'),
    (20, 12, 'reports',     15,  '2024-02-01'),
    (21, 13, 'api',         90,  '2024-02-01'),
    (22, 14, 'api',         30,  '2024-02-01'),
    (23, 15, 'dashboards',  20,  '2024-02-01'),
    (24, 15, 'api',         60,  '2024-02-01');
