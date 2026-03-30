---
materialization: table
macros: [qraft_utils.scalar, ecommerce_utils]
description: Customer-level business summary with tier classification
tags: [gold]
columns:
  - name: customer_id
    description: Unique customer identifier
    tests:
      - not_null
      - unique
  - name: total_orders
    description: Number of orders placed
    tests:
      - accepted_range:
          min_value: 0
  - name: lifetime_spend
    description: Total amount spent
    tests:
      - accepted_range:
          min_value: 0
  - name: customer_tier
    description: Tier based on lifetime spend
    tests:
      - accepted_values:
          values: [bronze, silver, gold]
---
SELECT
    c.customer_id,
    c.customer_name,
    c.email,
    c.country,
    c.created_at                             AS customer_since,
    coalesce_zero(COUNT(o.order_id))         AS total_orders,
    coalesce_zero(SUM(o.order_total))        AS lifetime_spend,
    safe_divide(SUM(o.order_total), COUNT(o.order_id))
                                             AS avg_order_value,
    MAX(o.order_date)                        AS last_order_date,
    classify_tier(SUM(o.order_total))        AS customer_tier
FROM ref('stg_customers') c
LEFT JOIN ref('int_orders_enriched') o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name, c.email, c.country, c.created_at
