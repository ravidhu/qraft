---
materialization: ephemeral
description: Sales pipeline aggregation per account (injected as CTE)
tags: [silver, crm]
---
SELECT
    o.account_id,
    COUNT(DISTINCT o.opportunity_id)                             AS total_opportunities,
    SUM(CASE WHEN o.stage = 'closed_won' THEN o.deal_amount ELSE 0 END)
                                                                  AS closed_won_amount,
    SUM(CASE WHEN o.stage = 'closed_lost' THEN o.deal_amount ELSE 0 END)
                                                                  AS closed_lost_amount,
    SUM(CASE WHEN o.stage NOT IN ('closed_won','closed_lost') THEN o.deal_amount ELSE 0 END)
                                                                  AS pipeline_amount,
    COUNT(CASE WHEN o.stage = 'closed_won' THEN 1 END)           AS won_count,
    COUNT(CASE WHEN o.stage = 'closed_lost' THEN 1 END)          AS lost_count
FROM ref('stg_opportunities') o
GROUP BY o.account_id
