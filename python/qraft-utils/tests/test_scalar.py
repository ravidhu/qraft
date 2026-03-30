from qraft_utils.engine import Engine
from qraft_utils.scalar import (
    surrogate_key,
    safe_divide,
    cents_to_dollars,
    coalesce_zero,
    bool_or,
    generate_surrogate_key,
)


# --- surrogate_key ---

def test_surrogate_key_single_column():
    result = surrogate_key("id", vars={})
    assert result == "md5(CAST(id AS VARCHAR))"


def test_surrogate_key_multiple_columns():
    result = surrogate_key("customer_id", "order_date", vars={})
    assert "CAST(customer_id AS VARCHAR)" in result
    assert "CAST(order_date AS VARCHAR)" in result
    assert " || '-' || " in result


def test_surrogate_key_postgres():
    result = surrogate_key("a", "b", vars={"engine": Engine.POSTGRES})
    assert result == "md5(CAST(a AS VARCHAR) || '-' || CAST(b AS VARCHAR))"


def test_surrogate_key_duckdb():
    result = surrogate_key("a", "b", vars={"engine": Engine.DUCKDB})
    assert result == "md5(CAST(a AS VARCHAR) || '-' || CAST(b AS VARCHAR))"


def test_surrogate_key_mysql():
    result = surrogate_key("a", "b", vars={"engine": Engine.MYSQL})
    assert result == "MD5(CONCAT(CAST(a AS CHAR), '-', CAST(b AS CHAR)))"


def test_surrogate_key_mysql_single():
    result = surrogate_key("id", vars={"engine": Engine.MYSQL})
    assert result == "MD5(CONCAT(CAST(id AS CHAR)))"


def test_surrogate_key_trino():
    result = surrogate_key("a", "b", vars={"engine": Engine.TRINO})
    assert result == "to_hex(md5(to_utf8(CAST(a AS VARCHAR) || '-' || CAST(b AS VARCHAR))))"


# --- safe_divide ---

def test_safe_divide():
    result = safe_divide("revenue", "order_count", vars={})
    assert "CASE WHEN order_count = 0 THEN NULL" in result
    assert "revenue / order_count" in result


def test_safe_divide_with_expressions():
    result = safe_divide("SUM(revenue)", "COUNT(*)", vars={})
    assert "SUM(revenue) / COUNT(*)" in result


# --- cents_to_dollars ---

def test_cents_to_dollars():
    result = cents_to_dollars("amount_cents", vars={})
    assert result == "(amount_cents / 100.0)"


# --- coalesce_zero ---

def test_coalesce_zero():
    result = coalesce_zero("lifetime_spend", vars={})
    assert result == "COALESCE(lifetime_spend, 0)"


# --- bool_or ---

def test_bool_or():
    result = bool_or("is_returned", vars={})
    assert "MAX(CASE WHEN is_returned THEN 1 ELSE 0 END) = 1" in result


# --- generate_surrogate_key ---

def test_generate_surrogate_key_is_alias():
    result1 = surrogate_key("a", "b", vars={})
    result2 = generate_surrogate_key("a", "b", vars={})
    assert result1 == result2


def test_generate_surrogate_key_mysql():
    result1 = surrogate_key("a", vars={"engine": Engine.MYSQL})
    result2 = generate_surrogate_key("a", vars={"engine": Engine.MYSQL})
    assert result1 == result2
