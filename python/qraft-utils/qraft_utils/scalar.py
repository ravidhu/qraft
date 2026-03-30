"""Column-level scalar transforms.

The most commonly used macro category. Each function takes column expressions
as positional args + `vars` keyword, and returns a SQL fragment string.

Engine adaptation:
    vars["engine"] is injected automatically by qraft at compile time.
    Functions that generate engine-specific SQL branch on Engine enum.
    Supported engines: duckdb, postgres, mysql, trino.
    Default (when engine is missing): postgres-compatible SQL.

Adapted functions:
    - surrogate_key: MySQL uses CONCAT() instead of ||, Trino wraps md5 in to_hex().
    - generate_surrogate_key: alias for surrogate_key, same adaptations.
"""

from qraft_utils.engine import Engine

__all__ = [
    "surrogate_key",
    "safe_divide",
    "cents_to_dollars",
    "coalesce_zero",
    "bool_or",
    "generate_surrogate_key",
]


def surrogate_key(*cols, vars):
    """Generate an MD5 surrogate key from one or more columns.

    Engine differences:
        - duckdb/postgres: md5(CAST(a AS VARCHAR) || '-' || ...)
        - mysql:           MD5(CONCAT(CAST(a AS CHAR), '-', ...))
        - trino:           to_hex(md5(to_utf8(CAST(a AS VARCHAR) || '-' || ...)))
    """
    engine = Engine.from_vars(vars)
    casts = [f"CAST({c} AS VARCHAR)" for c in cols]

    if engine is Engine.MYSQL:
        casts = [f"CAST({c} AS CHAR)" for c in cols]
        inner = ", '-', ".join(casts)
        return f"MD5(CONCAT({inner}))"

    concat = " || '-' || ".join(casts)

    if engine is Engine.TRINO:
        return f"to_hex(md5(to_utf8({concat})))"

    # duckdb, postgres
    return f"md5({concat})"


def safe_divide(numerator, denominator, vars):
    """Division that returns NULL instead of dividing by zero."""
    return f"CASE WHEN {denominator} = 0 THEN NULL ELSE {numerator} / {denominator} END"


def cents_to_dollars(column, vars):
    """Currency conversion from cents to dollars."""
    return f"({column} / 100.0)"


def coalesce_zero(column, vars):
    """Null-safe coalesce to zero."""
    return f"COALESCE({column}, 0)"


def bool_or(column, vars):
    """Boolean OR aggregation — returns true if any row in the group has a truthy value."""
    return f"MAX(CASE WHEN {column} THEN 1 ELSE 0 END) = 1"


def generate_surrogate_key(*cols, vars):
    """Alias for surrogate_key. Matches the dbt-utils naming for easier migration."""
    return surrogate_key(*cols, vars=vars)
