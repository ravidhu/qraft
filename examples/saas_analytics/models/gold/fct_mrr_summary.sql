---
materialization: table
description: MRR summary by plan and company segment
tags: [gold, revenue]
---
SELECT
    ae.plan_name,
    ae.company_size,
    COUNT(DISTINCT ae.account_id)                                 AS account_count,
    SUM(CASE WHEN ae.subscription_status = 'active' THEN ae.mrr ELSE 0 END)
                                                                  AS active_mrr,
    SUM(CASE WHEN ae.subscription_status = 'cancelled' THEN ae.mrr ELSE 0 END)
                                                                  AS churned_mrr,
    AVG(CASE WHEN ae.subscription_status = 'active' THEN ae.mrr END)
                                                                  AS avg_mrr_per_account,
    SUM(CASE WHEN ae.subscription_status = 'active' THEN ae.mrr ELSE 0 END) * 12
                                                                  AS projected_arr
FROM ref('int_accounts_enriched') ae
GROUP BY ae.plan_name, ae.company_size
