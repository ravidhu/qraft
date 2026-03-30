"""Structural SQL generation.

Macros that generate variable-length SQL structures like pivots, unions, and star-except.
"""

__all__ = [
    "pivot",
    "pivot_agg",
    "union_relations",
    "star_except",
]


def pivot(column, *values, vars):
    """Generate CASE-WHEN pivot columns from a list of values."""
    agg = vars.get("pivot_agg", "SUM")
    cases = []
    for v in values:
        clean = v.strip().strip("'")
        cases.append(
            f"{agg}(CASE WHEN {column} = '{clean}' THEN 1 ELSE 0 END) AS {clean}"
        )
    return ",\n    ".join(cases)


def pivot_agg(column, value_column, *values, vars):
    """Pivot with a custom value column (not just counting)."""
    agg = vars.get("pivot_agg", "SUM")
    cases = []
    for v in values:
        clean = v.strip().strip("'")
        cases.append(
            f"{agg}(CASE WHEN {column} = '{clean}' THEN {value_column} END) AS {value_column}_{clean}"
        )
    return ",\n    ".join(cases)


def union_relations(*relations, vars):
    """Union multiple relations with a source-tracking column."""
    parts = []
    for rel in relations:
        clean = rel.strip().strip("'")
        parts.append(
            f"SELECT '{clean}' AS _source_relation, * FROM {clean}"
        )
    return "\nUNION ALL\n".join(parts)


def star_except(relation, *exclude_cols, vars):
    """Select all columns except the named ones.

    Requires vars["conn_str"] to query the information schema.
    """
    conn_str = vars.get("conn_str")
    if conn_str is None:
        raise ValueError(
            "star_except requires 'conn_str' in vars to query column metadata. "
            "Add conn_str to your project.yaml vars."
        )

    import sqlalchemy
    engine = sqlalchemy.create_engine(conn_str)

    clean_relation = relation.strip().strip("'")
    # Handle schema.table format
    parts = clean_relation.split(".")
    table_name = parts[-1]
    schema_name = parts[-2] if len(parts) > 1 else None

    with engine.connect() as conn:
        query = (
            "SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{table_name}'"
        )
        if schema_name:
            query += f" AND table_schema = '{schema_name}'"
        query += " ORDER BY ordinal_position"
        cols = [row[0] for row in conn.execute(sqlalchemy.text(query))]

    exclude = {c.strip().strip("'") for c in exclude_cols}
    keep = [c for c in cols if c not in exclude]
    if not keep:
        raise ValueError(
            f"star_except: all columns excluded from {clean_relation}. "
            f"Available columns: {cols}"
        )
    return ", ".join(keep)
