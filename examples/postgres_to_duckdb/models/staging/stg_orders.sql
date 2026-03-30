---
columns:
  - name: order_id
    description: Unique order identifier
    tests:
      - not_null
      - unique
  - name: user_id
    tests:
      - not_null
      - relationships:
          to: ref('stg_users')
          field: user_id
  - name: quantity
    tests:
      - accepted_range:
          min_value: 1
  - name: total
    tests:
      - accepted_range:
          min_value: 0
---
SELECT
    id         AS order_id,
    user_id,
    product_id,
    quantity,
    total,
    status,
    ordered_at
FROM source('app', 'orders')
WHERE status = 'completed'
