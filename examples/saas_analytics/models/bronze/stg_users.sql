---
description: Product platform users loaded from source
tags: [bronze, product]
---
SELECT
    id              AS user_id,
    account_id,
    email,
    role            AS user_role,
    created_at      AS user_created_at,
    last_active_at
FROM source('product', 'users')
