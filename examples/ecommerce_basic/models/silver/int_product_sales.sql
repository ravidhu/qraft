---
materialization: ephemeral
description: Product-level sales aggregation (injected as CTE into downstream models)
tags: [silver]
---
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.list_price,
    COUNT(DISTINCT oi.order_id)             AS times_ordered,
    SUM(oi.quantity)                         AS total_units_sold,
    SUM(oi.quantity * oi.unit_price)         AS total_revenue
FROM ref('stg_products') p
LEFT JOIN ref('stg_order_items') oi ON p.product_id = oi.product_id
LEFT JOIN ref('stg_orders') o ON oi.order_id = o.order_id AND o.status = 'completed'
GROUP BY p.product_id, p.product_name, p.category, p.list_price
