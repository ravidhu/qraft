---
materialization: table
description: Accounts enriched with subscription, contact, and user counts
tags: [silver, crm, billing]
---
SELECT
    a.account_id,
    a.account_name,
    a.industry,
    a.company_size,
    a.country,
    a.account_created_at,
    s.subscription_id,
    s.plan_name,
    s.mrr,
    s.status          AS subscription_status,
    s.started_at      AS subscription_started_at,
    s.cancelled_at,
    contact_counts.contact_count,
    user_counts.user_count
FROM ref('stg_accounts') a
LEFT JOIN ref('stg_subscriptions') s
    ON a.account_id = s.account_id
LEFT JOIN (
    SELECT account_id, COUNT(*) AS contact_count
    FROM ref('stg_contacts')
    GROUP BY account_id
) contact_counts ON a.account_id = contact_counts.account_id
LEFT JOIN (
    SELECT account_id, COUNT(*) AS user_count
    FROM ref('stg_users')
    GROUP BY account_id
) user_counts ON a.account_id = user_counts.account_id
