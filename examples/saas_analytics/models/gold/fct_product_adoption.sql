---
materialization: table
description: Product adoption metrics and scoring per account
tags: [gold, product]
---
SELECT
    ah.account_id,
    ah.account_name,
    ah.plan_name,
    ah.mrr,
    ah.health_status,
    ah.active_users,
    ah.api_calls,
    ah.dashboard_views,

    -- Feature adoption flags
    CASE WHEN ah.api_calls > 0 THEN 1 ELSE 0 END        AS uses_api,
    CASE WHEN ah.dashboard_views > 0 THEN 1 ELSE 0 END  AS uses_dashboards,

    -- Adoption score (0-100)
    LEAST(100, (
        (CASE WHEN ah.active_users > 0 THEN 25 ELSE 0 END) +
        (CASE WHEN ah.api_calls > 100 THEN 25 ELSE (ah.api_calls * 25 / 100) END) +
        (CASE WHEN ah.dashboard_views > 20 THEN 25 ELSE (ah.dashboard_views * 25 / 20) END) +
        (CASE WHEN ah.active_users >= ah.user_count AND ah.user_count > 0 THEN 25
              WHEN ah.user_count > 0 THEN (ah.active_users * 25 / ah.user_count)
              ELSE 0 END)
    ))                                                    AS adoption_score

FROM ref('fct_account_health') ah
WHERE ah.subscription_status = 'active'
