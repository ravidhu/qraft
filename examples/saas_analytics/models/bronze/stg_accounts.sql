---
description: CRM accounts loaded from source
tags: [bronze, crm]
columns:
  - name: account_id
    description: Unique account identifier
    tests:
      - not_null
      - unique
  - name: account_name
    description: Company name
    tests:
      - not_null
  - name: company_size
    description: Company size segment
    tests:
      - accepted_values:
          values: [startup, mid-market, enterprise]
---
SELECT
    id            AS account_id,
    name          AS account_name,
    industry,
    company_size,
    country,
    created_at    AS account_created_at
FROM source('crm', 'accounts')
