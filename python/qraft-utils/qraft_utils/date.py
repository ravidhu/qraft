"""Date spine and date utilities.

Date spine generation and date helpers for reporting models.

Engine adaptation:
    vars["engine"] is injected automatically by qraft at compile time.

Adapted functions:
    - date_spine: Each engine has a different way to generate date series.
    - fiscal_year_filter: MySQL has no DATE_TRUNC, uses DATE_FORMAT + STR_TO_DATE.
    - date_trunc_to: MySQL has no DATE_TRUNC, uses DATE_FORMAT-based truncation.
"""

from qraft_utils.engine import Engine

__all__ = [
    "date_spine",
    "fiscal_year_filter",
    "date_trunc_to",
]

# MySQL DATE_FORMAT patterns for DATE_TRUNC emulation.
_MYSQL_TRUNC_FORMATS = {
    "year": "%Y-01-01",
    "quarter": "quarter",  # special-cased below
    "month": "%Y-%m-01",
    "week": "week",  # special-cased below
    "day": "%Y-%m-%d",
}


def date_spine(start, end, vars):
    """Generate a date series from start to end (inclusive).

    Engine differences:
        - duckdb/postgres: generate_series(start::DATE, end::DATE, INTERVAL '1 day')
        - trino:           UNNEST(SEQUENCE(CAST(start AS DATE), CAST(end AS DATE),
                           INTERVAL '1' DAY))
        - mysql:           Recursive CTE (no generate_series support)

    Args:
        start: SQL date expression (e.g., "'2024-01-01'" or "DATE_TRUNC('year', CURRENT_DATE)")
        end: SQL date expression (e.g., "CURRENT_DATE")
    """
    engine = Engine.from_vars(vars)

    if engine is Engine.TRINO:
        return (
            f"SELECT CAST(d AS DATE) AS date_day "
            f"FROM UNNEST(SEQUENCE(CAST({start} AS DATE), CAST({end} AS DATE), "
            f"INTERVAL '1' DAY)) AS t(d)"
        )

    if engine is Engine.MYSQL:
        return (
            f"WITH RECURSIVE date_spine AS ("
            f"SELECT CAST({start} AS DATE) AS date_day "
            f"UNION ALL "
            f"SELECT date_day + INTERVAL 1 DAY FROM date_spine "
            f"WHERE date_day < {end}"
            f") SELECT date_day FROM date_spine"
        )

    # duckdb, postgres
    return (
        f"SELECT CAST(d AS DATE) AS date_day "
        f"FROM generate_series({start}::DATE, {end}::DATE, INTERVAL '1 day') AS t(d)"
    )


def fiscal_year_filter(date_column, vars):
    """Filter rows within the current fiscal year.

    Reads vars["fiscal_year_start_month"] (default: 4 for April).

    Engine differences:
        - duckdb/postgres/trino: DATE_TRUNC('year', CURRENT_DATE) + INTERVAL
        - mysql: DATE_FORMAT + STR_TO_DATE for year truncation + INTERVAL
    """
    engine = Engine.from_vars(vars)
    start_month = int(vars.get("fiscal_year_start_month", "4"))

    if engine is Engine.MYSQL:
        return (
            f"{date_column} >= STR_TO_DATE(DATE_FORMAT(CURRENT_DATE, '%Y-01-01'), '%Y-%m-%d') "
            f"+ INTERVAL {start_month - 1} MONTH "
            f"AND {date_column} < STR_TO_DATE(DATE_FORMAT(CURRENT_DATE, '%Y-01-01'), '%Y-%m-%d') "
            f"+ INTERVAL {start_month - 1 + 12} MONTH"
        )

    return (
        f"{date_column} >= DATE_TRUNC('year', CURRENT_DATE) "
        f"+ INTERVAL '{start_month - 1}' MONTH "
        f"AND {date_column} < DATE_TRUNC('year', CURRENT_DATE) "
        f"+ INTERVAL '{start_month - 1 + 12}' MONTH"
    )


def date_trunc_to(date_column, granularity, vars):
    """Truncate a date column to a given granularity.

    Engine differences:
        - duckdb/postgres/trino: DATE_TRUNC('month', col)
        - mysql: DATE_FORMAT(col, '%Y-%m-01') (varies by granularity)
    """
    engine = Engine.from_vars(vars)
    clean = granularity.strip().strip("'")

    if engine is Engine.MYSQL:
        fmt = _MYSQL_TRUNC_FORMATS.get(clean)
        if clean == "quarter":
            return (
                f"STR_TO_DATE(CONCAT(YEAR({date_column}), '-', "
                f"(QUARTER({date_column}) - 1) * 3 + 1, '-01'), '%Y-%m-%d')"
            )
        if clean == "week":
            return f"DATE_SUB({date_column}, INTERVAL WEEKDAY({date_column}) DAY)"
        if fmt is None:
            raise ValueError(
                f"date_trunc_to: unsupported granularity '{clean}' for MySQL. "
                f"Supported: {list(_MYSQL_TRUNC_FORMATS.keys())}"
            )
        return f"DATE_FORMAT({date_column}, '{fmt}')"

    return f"DATE_TRUNC('{clean}', {date_column})"
