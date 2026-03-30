---
description: Billing subscriptions loaded from source
tags: [bronze, billing]
columns:
  - name: subscription_id
    description: Unique subscription identifier
    tests:
      - not_null
      - unique
  - name: account_id
    description: Account this subscription belongs to
    tests:
      - not_null
      - relationships:
          to: ref('stg_accounts')
          field: account_id
  - name: status
    description: Subscription status
    tests:
      - accepted_values:
          values: [active, cancelled, trial, past_due]
  - name: mrr
    description: Monthly recurring revenue
    tests:
      - accepted_range:
          min_value: 0
---
SELECT
    id             AS subscription_id,
    account_id,
    plan           AS plan_name,
    mrr,
    status,
    started_at,
    cancelled_at
FROM source('billing', 'subscriptions')
