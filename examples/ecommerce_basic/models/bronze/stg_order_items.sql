---
description: Raw order line items loaded from source
tags: [bronze]
---
SELECT
    order_item_id AS item_id,
    order_id,
    product_id,
    quantity,
    unit_price
FROM source('raw', 'order_items')
