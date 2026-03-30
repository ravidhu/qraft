---
description: Billing payments loaded from source
tags: [bronze, billing]
---
SELECT
    id          AS payment_id,
    invoice_id,
    amount,
    method      AS payment_method,
    paid_at
FROM source('billing', 'payments')
