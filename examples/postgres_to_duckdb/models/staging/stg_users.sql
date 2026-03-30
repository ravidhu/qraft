---
columns:
  - name: user_id
    description: Unique user identifier
    tests:
      - not_null
      - unique
  - name: email
    description: User email address
    tests:
      - not_null
      - unique
  - name: plan
    description: Subscription plan
    tests:
      - accepted_values:
          values: [free, starter, pro, enterprise]
---
SELECT
    id         AS user_id,
    name       AS user_name,
    email,
    plan,
    created_at
FROM source('app', 'users')
