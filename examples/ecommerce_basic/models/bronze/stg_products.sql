---
description: Raw products loaded from source
tags: [bronze]
---
SELECT
    product_id,
    product_name,
    category,
    unit_price AS list_price
FROM source('raw', 'products')
