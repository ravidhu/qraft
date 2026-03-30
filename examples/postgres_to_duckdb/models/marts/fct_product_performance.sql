---
materialization: table
description: Product sales performance
tags: [marts]
---
SELECT
    p.product_id,
    p.product_name,
    p.price                               AS list_price,
    COUNT(DISTINCT o.order_id)            AS times_ordered,
    SUM(o.quantity)                        AS total_units_sold,
    SUM(o.total)                          AS total_revenue
FROM ref('stg_products') p
LEFT JOIN ref('stg_orders') o ON p.product_id = o.product_id
GROUP BY p.product_id, p.product_name, p.price
