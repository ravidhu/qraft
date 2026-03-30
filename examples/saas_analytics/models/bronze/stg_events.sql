---
description: Product telemetry events loaded from source
tags: [bronze, product]
---
SELECT
    id          AS event_id,
    user_id,
    event_type,
    event_ts
FROM source('product', 'events')
