---
materialization: table_incremental
unique_key: account_id
macros: [saas_utils, qraft_utils.scalar]
description: Unified account health scorecard combining CRM, billing, and product data
tags: [gold, critical]
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
    ae.contact_count,
    ae.user_count,

    -- Revenue metrics
    coalesce_zero(rev.total_paid)        AS lifetime_revenue,
    coalesce_zero(rev.total_overdue)     AS overdue_amount,

    -- Sales pipeline
    coalesce_zero(sp.closed_won_amount)  AS total_won_deals,
    coalesce_zero(sp.pipeline_amount)    AS open_pipeline,

    -- Product engagement
    coalesce_zero(pe.active_users)       AS active_users,
    coalesce_zero(pe.total_events)       AS total_events,
    coalesce_zero(pe.api_calls)          AS api_calls,
    coalesce_zero(pe.dashboard_views)    AS dashboard_views,

    -- Health score via macro (uses vars: at_risk_event_threshold, healthy_mrr_threshold)
    health_score(ae.subscription_status, pe.active_users, pe.total_events, ae.mrr)
                                         AS health_status

FROM ref('int_accounts_enriched') ae
LEFT JOIN ref('int_revenue_by_account') rev  ON ae.account_id = rev.account_id
LEFT JOIN ref('int_sales_pipeline') sp       ON ae.account_id = sp.account_id
LEFT JOIN ref('int_product_engagement') pe   ON ae.account_id = pe.account_id
