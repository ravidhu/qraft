def classify_tier(amount_expr, vars):
    """Classify a customer into gold/silver/bronze based on spend thresholds from vars."""
    gold = vars["gold_threshold"]
    silver = vars["silver_threshold"]
    return (
        f"CASE"
        f" WHEN {amount_expr} >= {gold} THEN 'gold'"
        f" WHEN {amount_expr} >= {silver} THEN 'silver'"
        f" ELSE 'bronze'"
        f" END"
    )
