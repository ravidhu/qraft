from qraft_utils.engine import Engine
from qraft_utils.conditions import (
    is_valid_email,
    recency,
    not_deleted,
    accepted_values,
)


# --- is_valid_email ---

def test_is_valid_email():
    result = is_valid_email("email", vars={})
    assert "LIKE '%@%.%'" in result
    assert "LENGTH(email) > 5" in result


def test_is_valid_email_mysql():
    result = is_valid_email("email", vars={"engine": Engine.MYSQL})
    assert "LIKE '%@%.%'" in result
    assert "CHAR_LENGTH(email) > 5" in result
    assert "LENGTH" not in result.replace("CHAR_LENGTH", "")


def test_is_valid_email_trino():
    result = is_valid_email("email", vars={"engine": Engine.TRINO})
    assert "LENGTH(email) > 5" in result


# --- recency ---

def test_recency():
    result = recency("last_order_date", "90", vars={})
    assert "last_order_date >= CURRENT_DATE" in result
    assert "INTERVAL '90' DAY" in result


def test_recency_mysql():
    result = recency("last_order_date", "90", vars={"engine": Engine.MYSQL})
    assert "last_order_date >= CURRENT_DATE" in result
    assert "INTERVAL 90 DAY" in result
    assert "'" not in result.split("INTERVAL")[1]


def test_recency_trino():
    result = recency("last_order_date", "30", vars={"engine": Engine.TRINO})
    assert "INTERVAL '30' DAY" in result


# --- not_deleted ---

def test_not_deleted_default():
    result = not_deleted(vars={})
    assert result == "deleted_at IS NULL"


def test_not_deleted_custom_column():
    result = not_deleted("removed_at", vars={})
    assert result == "removed_at IS NULL"


# --- accepted_values ---

def test_accepted_values():
    result = accepted_values("status", "'active'", "'pending'", vars={})
    assert "status IN (" in result
    assert "'active'" in result
    assert "'pending'" in result
