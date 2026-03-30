---
materialization: ephemeral
description: Product engagement per account (injected as CTE)
tags: [silver, product]
---
SELECT
    u.account_id,
    COUNT(DISTINCT u.user_id)                        AS active_users,
    COUNT(DISTINCT e.event_id)                       AS total_events,
    MAX(u.last_active_at)                            AS last_active_at,
    SUM(CASE WHEN f.feature = 'api' THEN f.usage_count ELSE 0 END)
                                                     AS api_calls,
    SUM(CASE WHEN f.feature = 'dashboards' THEN f.usage_count ELSE 0 END)
                                                     AS dashboard_views,
    SUM(CASE WHEN f.feature = 'reports' THEN f.usage_count ELSE 0 END)
                                                     AS report_exports
FROM ref('stg_users') u
LEFT JOIN ref('stg_events') e ON u.user_id = e.user_id
LEFT JOIN ref('stg_feature_usage') f ON u.user_id = f.user_id
GROUP BY u.account_id
