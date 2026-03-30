---
materialization: table
description: Revenue aggregated per account from invoices and payments
tags: [silver, billing]
---
SELECT
    s.account_id,
    COUNT(DISTINCT i.invoice_id)                      AS total_invoices,
    SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END)  AS total_paid,
    SUM(CASE WHEN i.status = 'overdue' THEN i.amount ELSE 0 END) AS total_overdue,
    COUNT(DISTINCT p.payment_id)                      AS total_payments,
    MAX(p.paid_at)                                    AS last_payment_at
FROM ref('stg_subscriptions') s
LEFT JOIN ref('stg_invoices') i ON s.subscription_id = i.subscription_id
LEFT JOIN ref('stg_payments') p ON i.invoice_id = p.invoice_id
GROUP BY s.account_id
