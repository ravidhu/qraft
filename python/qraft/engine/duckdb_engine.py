import duckdb

from qraft.config.models import ConnectionConfig
from qraft.engine.base import ConnectionTestResult, Engine


class DuckDBEngine(Engine):
    def __init__(self) -> None:
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self, config: ConnectionConfig) -> None:
        path = config.params.get("path", ":memory:")
        self._conn = duckdb.connect(path)
        init_sql = config.params.get("init_sql")
        if init_sql:
            for stmt in init_sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    self._conn.execute(stmt)

    def execute(self, sql: str) -> None:
        self._conn.execute(sql)

    def query(self, sql: str) -> list[tuple]:
        result = self._conn.execute(sql)
        return result.fetchall()

    def create_schema(self, schema: str) -> None:
        self._conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    def drop(self, target: str, kind: str) -> None:
        self._conn.execute(f"DROP {kind.upper()} IF EXISTS {target}")

    def object_exists(self, target: str) -> bool:
        try:
            self._conn.execute(f"SELECT 1 FROM {target} LIMIT 0")
            return True
        except duckdb.Error:
            return False

    def test_connection(self) -> ConnectionTestResult:
        try:
            self._conn.execute("SELECT 1")
            return ConnectionTestResult(
                success=True, details="DuckDB connection OK"
            )
        except Exception as error:
            return ConnectionTestResult(success=False, details=str(error))

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
