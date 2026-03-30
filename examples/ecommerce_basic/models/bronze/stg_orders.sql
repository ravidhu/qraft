---
description: Raw orders loaded from source
tags: [bronze]
columns:
  - name: order_id
    description: Unique order identifier
    tests:
      - not_null
      - unique
  - name: customer_id
    description: Customer who placed the order
    tests:
      - not_null
      - relationships:
          to: ref('stg_customers')
          field: customer_id
  - name: status
    description: Order status
    tests:
      - accepted_values:
          values: [pending, shipped, delivered, cancelled, completed]
---
SELECT
    order_id,
    customer_id,
    order_date,
    status
FROM source('raw', 'orders')
