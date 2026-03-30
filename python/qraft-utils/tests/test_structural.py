import pytest

from qraft_utils.structural import (
    pivot,
    pivot_agg,
    union_relations,
    star_except,
)


def test_pivot_basic():
    result = pivot("status", "'pending'", "'complete'", vars={})
    assert "CASE WHEN status = 'pending'" in result
    assert "CASE WHEN status = 'complete'" in result
    assert "AS pending" in result
    assert "AS complete" in result


def test_pivot_custom_agg():
    result = pivot("status", "'active'", vars={"pivot_agg": "COUNT"})
    assert "COUNT(CASE WHEN" in result


def test_pivot_agg():
    result = pivot_agg("method", "amount", "'credit'", "'debit'", vars={})
    assert "THEN amount END" in result
    assert "AS amount_credit" in result
    assert "AS amount_debit" in result


def test_union_relations():
    result = union_relations("'schema.a'", "'schema.b'", vars={})
    assert "SELECT 'schema.a' AS _source_relation" in result
    assert "UNION ALL" in result
    assert "FROM schema.b" in result


def test_union_relations_single():
    result = union_relations("'schema.a'", vars={})
    assert "UNION ALL" not in result
    assert "FROM schema.a" in result


def test_star_except_missing_conn_str():
    with pytest.raises(ValueError, match="conn_str"):
        star_except("'table'", "'col_a'", vars={})
