---
description: CRM sales opportunities loaded from source
tags: [bronze, crm]
---
SELECT
    id           AS opportunity_id,
    account_id,
    stage,
    amount       AS deal_amount,
    close_date
FROM source('crm', 'opportunities')
