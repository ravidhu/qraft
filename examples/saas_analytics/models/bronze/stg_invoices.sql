---
description: Billing invoices loaded from source
tags: [bronze, billing]
---
SELECT
    id              AS invoice_id,
    subscription_id,
    amount,
    status,
    issued_at,
    paid_at
FROM source('billing', 'invoices')
