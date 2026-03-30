-- Seed data for postgres_to_duckdb example
-- Source: application database (PostgreSQL)

CREATE SCHEMA IF NOT EXISTS app_public;

CREATE TABLE app_public.users (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    plan       TEXT NOT NULL DEFAULT 'free',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

INSERT INTO app_public.users (id, name, email, plan, created_at) VALUES
    (1, 'Alice Chen',      'alice@example.com',   'pro',        '2023-06-01 10:00:00'),
    (2, 'Bob Martinez',    'bob@example.com',     'free',       '2023-08-15 14:00:00'),
    (3, 'Carol Wu',        'carol@example.com',   'enterprise', '2023-10-20 09:00:00'),
    (4, 'David Kim',       'david@example.com',   'pro',        '2024-01-05 11:00:00'),
    (5, 'Eva Johansson',   'eva@example.com',     'free',       '2024-03-12 16:00:00'),
    (6, 'Frank Nguyen',    'frank@example.com',   'pro',        '2024-05-01 08:00:00');

CREATE TABLE app_public.products (
    id    SERIAL PRIMARY KEY,
    name  TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

INSERT INTO app_public.products (id, name, price) VALUES
    (101, 'Widget A',  29.99),
    (102, 'Widget B',  49.99),
    (103, 'Widget C',  99.99),
    (104, 'Addon X',   14.99);

CREATE TABLE app_public.orders (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES app_public.users(id),
    product_id  INTEGER NOT NULL REFERENCES app_public.products(id),
    quantity    INTEGER NOT NULL DEFAULT 1,
    total       DECIMAL(10,2) NOT NULL,
    status      TEXT NOT NULL DEFAULT 'completed',
    ordered_at  TIMESTAMP NOT NULL DEFAULT now()
);

INSERT INTO app_public.orders (id, user_id, product_id, quantity, total, status, ordered_at) VALUES
    (1,  1, 101, 2,  59.98, 'completed', '2023-07-10 09:00:00'),
    (2,  1, 103, 1,  99.99, 'completed', '2023-09-15 14:00:00'),
    (3,  3, 102, 3, 149.97, 'completed', '2023-11-20 10:00:00'),
    (4,  2, 101, 1,  29.99, 'completed', '2024-01-05 11:00:00'),
    (5,  4, 103, 1,  99.99, 'completed', '2024-02-14 16:00:00'),
    (6,  3, 104, 5,  74.95, 'completed', '2024-03-01 09:00:00'),
    (7,  1, 102, 1,  49.99, 'completed', '2024-04-10 13:00:00'),
    (8,  6, 101, 1,  29.99, 'completed', '2024-05-20 08:00:00'),
    (9,  5, 104, 2,  29.98, 'cancelled', '2024-06-01 15:00:00'),
    (10, 4, 102, 2,  99.98, 'completed', '2024-06-15 10:00:00');
