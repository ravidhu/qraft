---
materialization: table
description: Per-user order summary
tags: [marts]
columns:
  - name: user_id
    description: Unique user identifier
    tests:
      - not_null
      - unique
  - name: total_orders
    description: Number of completed orders
    tests:
      - accepted_range:
          min_value: 0
  - name: lifetime_spend
    description: Total amount spent
    tests:
      - accepted_range:
          min_value: 0
---
SELECT
    u.user_id,
    u.user_name,
    u.email,
    u.plan,
    u.created_at                          AS signed_up_at,
    COUNT(o.order_id)                     AS total_orders,
    COALESCE(SUM(o.total), 0)            AS lifetime_spend,
    MAX(o.ordered_at)                     AS last_order_at
FROM ref('stg_users') u
LEFT JOIN ref('stg_orders') o ON u.user_id = o.user_id
GROUP BY u.user_id, u.user_name, u.email, u.plan, u.created_at
