import pytest

from qraft_utils.engine import Engine
from qraft_utils.date import (
    date_spine,
    fiscal_year_filter,
    date_trunc_to,
)


# --- date_spine ---

def test_date_spine_default():
    result = date_spine("'2024-01-01'", "CURRENT_DATE", vars={})
    assert "generate_series" in result
    assert "'2024-01-01'" in result
    assert "CURRENT_DATE" in result


def test_date_spine_postgres():
    result = date_spine("'2024-01-01'", "CURRENT_DATE", vars={"engine": Engine.POSTGRES})
    assert "generate_series(" in result
    assert "::DATE" in result


def test_date_spine_duckdb():
    result = date_spine("'2024-01-01'", "CURRENT_DATE", vars={"engine": Engine.DUCKDB})
    assert "generate_series(" in result


def test_date_spine_trino():
    result = date_spine("'2024-01-01'", "CURRENT_DATE", vars={"engine": Engine.TRINO})
    assert "UNNEST(SEQUENCE(" in result
    assert "CAST(" in result
    assert "INTERVAL '1' DAY" in result


def test_date_spine_mysql():
    result = date_spine("'2024-01-01'", "CURRENT_DATE", vars={"engine": Engine.MYSQL})
    assert "RECURSIVE date_spine" in result
    assert "UNION ALL" in result
    assert "INTERVAL 1 DAY" in result


# --- fiscal_year_filter ---

def test_fiscal_year_filter_default():
    result = fiscal_year_filter("order_date", vars={})
    assert "order_date >=" in result
    assert "INTERVAL '3' MONTH" in result  # April = month 4, so 4-1=3


def test_fiscal_year_filter_custom():
    result = fiscal_year_filter("order_date", vars={"fiscal_year_start_month": "1"})
    assert "INTERVAL '0' MONTH" in result  # January start


def test_fiscal_year_filter_mysql():
    result = fiscal_year_filter("order_date", vars={"engine": Engine.MYSQL})
    assert "STR_TO_DATE" in result
    assert "DATE_FORMAT" in result
    assert "INTERVAL 3 MONTH" in result


def test_fiscal_year_filter_mysql_custom():
    result = fiscal_year_filter(
        "order_date", vars={"engine": Engine.MYSQL, "fiscal_year_start_month": "7"}
    )
    assert "INTERVAL 6 MONTH" in result  # July = 7, so 7-1=6


# --- date_trunc_to ---

def test_date_trunc_to():
    result = date_trunc_to("created_at", "'month'", vars={})
    assert result == "DATE_TRUNC('month', created_at)"


def test_date_trunc_to_trino():
    result = date_trunc_to("created_at", "'month'", vars={"engine": Engine.TRINO})
    assert result == "DATE_TRUNC('month', created_at)"


def test_date_trunc_to_mysql_month():
    result = date_trunc_to("created_at", "'month'", vars={"engine": Engine.MYSQL})
    assert result == "DATE_FORMAT(created_at, '%Y-%m-01')"


def test_date_trunc_to_mysql_year():
    result = date_trunc_to("created_at", "'year'", vars={"engine": Engine.MYSQL})
    assert result == "DATE_FORMAT(created_at, '%Y-01-01')"


def test_date_trunc_to_mysql_day():
    result = date_trunc_to("created_at", "'day'", vars={"engine": Engine.MYSQL})
    assert result == "DATE_FORMAT(created_at, '%Y-%m-%d')"


def test_date_trunc_to_mysql_quarter():
    result = date_trunc_to("created_at", "'quarter'", vars={"engine": Engine.MYSQL})
    assert "QUARTER(created_at)" in result
    assert "YEAR(created_at)" in result


def test_date_trunc_to_mysql_week():
    result = date_trunc_to("created_at", "'week'", vars={"engine": Engine.MYSQL})
    assert "WEEKDAY(created_at)" in result


def test_date_trunc_to_mysql_unsupported():
    with pytest.raises(ValueError, match="unsupported granularity"):
        date_trunc_to("created_at", "'hour'", vars={"engine": Engine.MYSQL})
