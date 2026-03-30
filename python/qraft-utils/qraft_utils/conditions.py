"""Reusable WHERE/HAVING conditions.

Each function returns a SQL boolean expression string.

Engine adaptation:
    vars["engine"] is injected automatically by qraft at compile time.

Adapted functions:
    - is_valid_email: MySQL uses CHAR_LENGTH instead of LENGTH.
    - recency: MySQL uses unquoted INTERVAL syntax (INTERVAL 90 DAY).
"""

from qraft_utils.engine import Engine

__all__ = [
    "is_valid_email",
    "recency",
    "not_deleted",
    "accepted_values",
]


def is_valid_email(column, vars):
    """Basic email format validation.

    Engine differences:
        - duckdb/postgres/trino: LENGTH()
        - mysql:                 CHAR_LENGTH() (correct for multibyte strings)
    """
    engine = Engine.from_vars(vars)
    length_fn = "CHAR_LENGTH" if engine is Engine.MYSQL else "LENGTH"
    return f"{column} LIKE '%@%.%' AND {length_fn}({column}) > 5"


def recency(date_column, days, vars):
    """Date-based recency filter.

    Engine differences:
        - duckdb/postgres/trino: INTERVAL '90' DAY
        - mysql:                 INTERVAL 90 DAY (no quotes around value)
    """
    engine = Engine.from_vars(vars)
    if engine is Engine.MYSQL:
        return f"{date_column} >= CURRENT_DATE - INTERVAL {days} DAY"
    return f"{date_column} >= CURRENT_DATE - INTERVAL '{days}' DAY"


def not_deleted(column="deleted_at", vars={}):
    """Soft-delete filter. Defaults to deleted_at if no column provided."""
    return f"{column} IS NULL"


def accepted_values(column, *values, vars):
    """Check that a column contains only the specified values."""
    quoted = ", ".join(f"'{v.strip(chr(39))}'" for v in values)
    return f"{column} IN ({quoted})"
