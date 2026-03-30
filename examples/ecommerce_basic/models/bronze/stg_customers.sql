---
description: Raw customers loaded from source
tags: [bronze]
columns:
  - name: customer_id
    description: Unique customer identifier
    tests:
      - not_null
      - unique
  - name: email
    description: Customer email address
    tests:
      - not_null
      - unique
---
SELECT
    customer_id,
    customer_name,
    email,
    country,
    created_at
FROM source('raw', 'customers')
