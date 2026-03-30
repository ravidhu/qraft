def health_score(status_expr, users_expr, events_expr, mrr_expr, vars):
    """Compute account health status based on subscription, usage, and revenue."""
    event_threshold = vars["at_risk_event_threshold"]
    mrr_threshold = vars["healthy_mrr_threshold"]
    return (
        f"CASE"
        f" WHEN {status_expr} = 'cancelled' THEN 'churned'"
        f" WHEN COALESCE({users_expr}, 0) = 0 THEN 'at_risk'"
        f" WHEN COALESCE({events_expr}, 0) < {event_threshold}"
        f" AND {mrr_expr} > {mrr_threshold} / 2 THEN 'at_risk'"
        f" WHEN {mrr_expr} >= {mrr_threshold}"
        f" AND COALESCE({users_expr}, 0) >= 2 THEN 'healthy'"
        f" WHEN {mrr_expr} >= 1000 THEN 'stable'"
        f" ELSE 'monitor'"
        f" END"
    )


def revenue_tier(mrr_expr, vars):
    """Classify accounts into revenue tiers based on MRR."""
    return (
        f"CASE"
        f" WHEN {mrr_expr} >= 10000 THEN 'Tier 1'"
        f" WHEN {mrr_expr} >= 3000 THEN 'Tier 2'"
        f" WHEN {mrr_expr} >= 1000 THEN 'Tier 3'"
        f" ELSE 'Tier 4'"
        f" END"
    )
