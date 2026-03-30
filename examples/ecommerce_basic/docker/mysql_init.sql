-- Seed data for ecommerce_basic example
-- Source: e-commerce application database (MariaDB)
-- MariaDB auto-creates the 'raw' database via MARIADB_DATABASE env var

USE raw;

-- Customers
CREATE TABLE customers (
    customer_id   INT PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    email         VARCHAR(150) NOT NULL,
    country       VARCHAR(50)  NOT NULL,
    created_at    DATE         NOT NULL
);

INSERT INTO customers (customer_id, customer_name, email, country, created_at) VALUES
    (1,  'Lena Rossi',     'lena@example.com',     'Italy',    '2022-03-15'),
    (2,  'James Okafor',   'james@example.com',    'Nigeria',  '2022-06-01'),
    (3,  'Mei Tanaka',     'mei@example.com',      'Japan',    '2022-08-20'),
    (4,  'Carlos Silva',   'carlos@example.com',   'Brazil',   '2023-01-10'),
    (5,  'Anna Petrov',    'anna@example.com',     'Russia',   '2023-03-25'),
    (6,  'Tom Nguyen',     'tom@example.com',      'Vietnam',  '2023-05-14'),
    (7,  'Sarah Mitchell', 'sarah@example.com',    'USA',      '2023-07-08'),
    (8,  'Omar Farouk',    'omar@example.com',     'Egypt',    '2023-09-19');

-- Products
CREATE TABLE products (
    product_id    INT PRIMARY KEY,
    product_name  VARCHAR(100) NOT NULL,
    category      VARCHAR(50)  NOT NULL,
    unit_price    DECIMAL(10,2) NOT NULL
);

INSERT INTO products (product_id, product_name, category, unit_price) VALUES
    (101, 'Wireless Mouse',      'Electronics',  29.99),
    (102, 'Mechanical Keyboard', 'Electronics',  89.99),
    (103, 'USB-C Hub',           'Electronics',  45.00),
    (104, 'Notebook (A5)',       'Stationery',   12.50),
    (105, 'Gel Pen Set',         'Stationery',    8.99),
    (106, 'Desk Lamp',           'Home Office',  54.00),
    (107, 'Monitor Stand',       'Home Office',  39.99),
    (108, 'Webcam HD',           'Electronics', 65.00);

-- Orders
CREATE TABLE orders (
    order_id    INT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date  DATE NOT NULL,
    status      VARCHAR(20) NOT NULL
);

INSERT INTO orders (order_id, customer_id, order_date, status) VALUES
    (1001, 1, '2023-01-20', 'completed'),
    (1002, 2, '2023-02-14', 'completed'),
    (1003, 1, '2023-03-05', 'completed'),
    (1004, 3, '2023-04-12', 'completed'),
    (1005, 4, '2023-05-01', 'completed'),
    (1006, 5, '2023-06-18', 'completed'),
    (1007, 2, '2023-07-22', 'completed'),
    (1008, 6, '2023-08-10', 'completed'),
    (1009, 7, '2023-09-03', 'cancelled'),
    (1010, 3, '2023-10-15', 'completed'),
    (1011, 8, '2023-11-28', 'completed'),
    (1012, 1, '2024-01-05', 'completed');

-- Order items
CREATE TABLE order_items (
    order_item_id INT PRIMARY KEY,
    order_id      INT NOT NULL,
    product_id    INT NOT NULL,
    quantity      INT NOT NULL,
    unit_price    DECIMAL(10,2) NOT NULL
);

INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price) VALUES
    (1,  1001, 101, 1, 29.99),
    (2,  1001, 104, 3, 12.50),
    (3,  1002, 102, 1, 89.99),
    (4,  1002, 105, 2,  8.99),
    (5,  1003, 106, 1, 54.00),
    (6,  1003, 103, 1, 45.00),
    (7,  1004, 101, 2, 29.99),
    (8,  1004, 107, 1, 39.99),
    (9,  1005, 108, 1, 65.00),
    (10, 1005, 104, 5, 12.50),
    (11, 1006, 102, 1, 89.99),
    (12, 1006, 106, 1, 54.00),
    (13, 1007, 103, 2, 45.00),
    (14, 1007, 105, 1,  8.99),
    (15, 1008, 101, 1, 29.99),
    (16, 1008, 108, 1, 65.00),
    (17, 1009, 107, 1, 39.99),
    (18, 1010, 102, 1, 89.99),
    (19, 1010, 104, 2, 12.50),
    (20, 1011, 106, 2, 54.00),
    (21, 1012, 101, 1, 29.99),
    (22, 1012, 103, 1, 45.00),
    (23, 1012, 105, 3,  8.99);
