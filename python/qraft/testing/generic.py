from qraft.testing.models import DataTestDefinition


def generate_test_sql(test: DataTestDefinition, target: str) -> str:
    """Generate a SQL query for a generic data test.

    The query returns failing rows — 0 rows = test passes.
    `target` is the fully qualified table name (e.g., "analytics.orders").
    """
    generators = {
        "not_null": _not_null,
        "unique": _unique,
        "accepted_values": _accepted_values,
        "relationships": _relationships,
        "number_of_rows": _number_of_rows,
        "accepted_range": _accepted_range,
        "unique_combination_of_columns": _unique_combination_of_columns,
    }

    generator = generators.get(test.test_type)
    if generator is None:
        raise ValueError(f"Unknown test type: '{test.test_type}'")

    sql = generator(test, target)

    # Apply WHERE filter if specified
    if test.where:
        sql = _apply_where(sql, test.where)

    return sql


def _not_null(test: DataTestDefinition, target: str) -> str:
    return f"SELECT * FROM {target} WHERE {test.column} IS NULL"


def _unique(test: DataTestDefinition, target: str) -> str:
    return (
        f"SELECT {test.column}, COUNT(*) AS _qraft_count "
        f"FROM {target} "
        f"GROUP BY {test.column} "
        f"HAVING COUNT(*) > 1"
    )


def _accepted_values(test: DataTestDefinition, target: str) -> str:
    values = test.params.get("values", [])
    if not values:
        raise ValueError(
            f"accepted_values test on {test.model_name}.{test.column} "
            f"requires a 'values' parameter"
        )
    quoted = ", ".join(f"'{v}'" for v in values)
    return (
        f"SELECT * FROM {target} "
        f"WHERE {test.column} NOT IN ({quoted})"
    )


def _relationships(test: DataTestDefinition, target: str) -> str:
    to = test.params.get("to")
    field = test.params.get("field")
    if not to or not field:
        raise ValueError(
            f"relationships test on {test.model_name}.{test.column} "
            f"requires 'to' and 'field' parameters"
        )
    # `to` is expected as ref('model_name') — extract the model name
    # and qualify it with the same schema as the target
    ref_model = _extract_ref(to)
    if ref_model:
        schema = target.rsplit(".", 1)[0]
        ref_target = f"{schema}.{ref_model}"
    else:
        ref_target = to

    return (
        f"SELECT * FROM {target} "
        f"WHERE {test.column} IS NOT NULL "
        f"AND {test.column} NOT IN (SELECT {field} FROM {ref_target})"
    )


def _number_of_rows(test: DataTestDefinition, target: str) -> str:
    min_rows = test.params.get("min_value", test.params.get("min", 1))
    return (
        f"SELECT CASE WHEN COUNT(*) < {min_rows} THEN 1 ELSE 0 END "
        f"AS _qraft_fail FROM {target} "
        f"HAVING COUNT(*) < {min_rows}"
    )


def _accepted_range(test: DataTestDefinition, target: str) -> str:
    conditions = []
    min_val = test.params.get("min_value", test.params.get("min"))
    max_val = test.params.get("max_value", test.params.get("max"))
    if min_val is not None:
        conditions.append(f"{test.column} < {min_val}")
    if max_val is not None:
        conditions.append(f"{test.column} > {max_val}")
    if not conditions:
        raise ValueError(
            f"accepted_range test on {test.model_name}.{test.column} "
            f"requires at least 'min' or 'max' parameter"
        )
    where = " OR ".join(conditions)
    return f"SELECT * FROM {target} WHERE {where}"


def _unique_combination_of_columns(test: DataTestDefinition, target: str) -> str:
    columns = test.params.get("combination", test.params.get("columns", []))
    if not columns:
        raise ValueError(
            f"unique_combination_of_columns test on {test.model_name} "
            f"requires a 'columns' parameter"
        )
    cols_str = ", ".join(columns)
    return (
        f"SELECT {cols_str}, COUNT(*) AS _qraft_count "
        f"FROM {target} "
        f"GROUP BY {cols_str} "
        f"HAVING COUNT(*) > 1"
    )


def _extract_ref(ref_str: str) -> str | None:
    """Extract model name from ref('model_name') syntax."""
    ref_str = ref_str.strip()
    for prefix, suffix in [("ref('", "')"), ('ref("', '")')]:
        if ref_str.startswith(prefix) and ref_str.endswith(suffix):
            return ref_str[len(prefix):-len(suffix)]
    return None


def _apply_where(sql: str, where_clause: str) -> str:
    """Wrap the test SQL with an additional WHERE filter.

    Wraps in a subquery to avoid conflicts with GROUP BY / HAVING.
    """
    return (
        f"SELECT * FROM ({sql}) _qraft_filtered "
        f"WHERE {where_clause}"
    )
