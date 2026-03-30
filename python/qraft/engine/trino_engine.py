import trino

from qraft.config.models import ConnectionConfig
from qraft.engine.base import ConnectionTestResult, Engine


class TrinoEngine(Engine):
    def __init__(self) -> None:
        self._conn: trino.dbapi.Connection | None = None
        self._catalog: str = ""

    def connect(self, config: ConnectionConfig) -> None:
        self._catalog = config.params.get("catalog", "")
        connect_kwargs: dict = {
            "host": config.params.get("host", "localhost"),
            "port": int(config.params.get("port", "8080")),
            "user": config.params.get("user", "trino"),
            "catalog": self._catalog,
        }
        if "schema" in config.params:
            connect_kwargs["schema"] = config.params["schema"]
        if "http_scheme" in config.params:
            connect_kwargs["http_scheme"] = config.params["http_scheme"]
        if "roles" in config.params:
            connect_kwargs["roles"] = config.params["roles"]

        self._conn = trino.dbapi.connect(**connect_kwargs)

    def execute(self, sql: str) -> None:
        # Trino requires fetching results to trigger execution.
        # Split multi-statement DDL and execute each separately.
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        cur = self._conn.cursor()
        try:
            for stmt in statements:
                cur.execute(stmt)
                cur.fetchall()
        finally:
            cur.close()

    def query(self, sql: str) -> list[tuple]:
        cur = self._conn.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            return [tuple(r) for r in rows]
        finally:
            cur.close()

    def create_schema(self, schema: str) -> None:
        cur = self._conn.cursor()
        try:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            cur.fetchall()
        finally:
            cur.close()

    def drop(self, target: str, kind: str) -> None:
        cur = self._conn.cursor()
        try:
            cur.execute(f"DROP {kind.upper()} IF EXISTS {target}")
            cur.fetchall()
        except trino.exceptions.TrinoUserError:
            pass  # Object may not exist in some connectors
        finally:
            cur.close()

    def object_exists(self, target: str) -> bool:
        parts = target.split(".")
        table_name = parts[-1]
        schema = parts[-2] if len(parts) >= 2 else "default"
        cur = self._conn.cursor()
        try:
            cur.execute(
                f"SHOW TABLES FROM {schema} LIKE '{table_name}'"
            )
            rows = cur.fetchall()
            return len(rows) > 0
        except trino.exceptions.TrinoUserError:
            return False
        finally:
            cur.close()

    def test_connection(self) -> ConnectionTestResult:
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchall()
            cur.close()
            return ConnectionTestResult(
                success=True, details="Trino connection OK"
            )
        except Exception as error:
            return ConnectionTestResult(success=False, details=str(error))

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
