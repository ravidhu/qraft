---
materialization: table
macros: [qraft_utils.scalar]
description: Revenue breakdown by product category
tags: [gold]
---
SELECT
    ps.category,
    COUNT(DISTINCT ps.product_id)   AS product_count,
    SUM(ps.total_units_sold)        AS units_sold,
    SUM(ps.total_revenue)           AS total_revenue,
    AVG(ps.list_price)              AS avg_list_price,
    safe_divide(SUM(ps.total_revenue) * 100.0, SUM(SUM(ps.total_revenue)) OVER ())
                                    AS revenue_pct
FROM ref('int_product_sales') ps
GROUP BY ps.category
