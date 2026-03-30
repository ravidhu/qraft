---
materialization: table
schema: dimensions
macros: [saas_utils]
description: Account dimension table for BI/reporting (Type 1 SCD)
tags: [gold, dimension]
---
SELECT
    ae.account_id,
    ae.account_name,
    ae.industry,
    ae.company_size,
    ae.country,
    ae.account_created_at,
    ae.plan_name,
    ae.mrr,
    ae.subscription_status,
    ae.subscription_started_at,
    ae.cancelled_at,
    ae.contact_count,
    ae.user_count,
    CASE
        WHEN ae.company_size = 'enterprise' THEN 'Enterprise'
        WHEN ae.company_size = 'mid-market' THEN 'Mid-Market'
        WHEN ae.company_size = 'startup'    THEN 'Startup'
        ELSE 'Unknown'
    END                     AS segment_label,
    revenue_tier(ae.mrr)    AS revenue_tier
FROM ref('int_accounts_enriched') ae
