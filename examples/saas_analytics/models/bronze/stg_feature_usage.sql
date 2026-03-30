---
description: Product feature usage metrics loaded from source
tags: [bronze, product]
---
SELECT
    user_id,
    feature,
    usage_count,
    period
FROM source('product', 'feature_usage')
