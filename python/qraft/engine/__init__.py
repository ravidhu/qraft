from qraft.engine.base import Engine


def get_engine(engine_type: str) -> Engine:
    """Factory for DB engines (lazy imports to avoid requiring all drivers)."""
    if engine_type == "duckdb":
        from qraft.engine.duckdb_engine import DuckDBEngine

        return DuckDBEngine()
    elif engine_type == "postgres":
        from qraft.engine.postgres_engine import PostgresEngine

        return PostgresEngine()
    elif engine_type == "mysql":
        from qraft.engine.mysql_engine import MySQLEngine

        return MySQLEngine()
    elif engine_type == "trino":
        from qraft.engine.trino_engine import TrinoEngine

        return TrinoEngine()
    else:
        raise ValueError(f"Unsupported engine type: {engine_type}")
