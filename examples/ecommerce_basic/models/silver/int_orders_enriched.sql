---
materialization: table
description: Orders enriched with line-item totals, filtered to completed only
tags: [silver]
---
SELECT
    o.order_id,
    o.customer_id,
    o.order_date,
    o.status,
    COUNT(oi.item_id)                       AS item_count,
    SUM(oi.quantity)                         AS total_quantity,
    SUM(oi.quantity * oi.unit_price)         AS order_total
FROM ref('stg_orders') o
LEFT JOIN ref('stg_order_items') oi ON o.order_id = oi.order_id
WHERE o.status = 'completed'
GROUP BY o.order_id, o.customer_id, o.order_date, o.status
HAVING SUM(oi.quantity * oi.unit_price) >= {{ min_order_amount }}
