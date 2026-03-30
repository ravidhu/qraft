import pymysql

from qraft.config.models import ConnectionConfig
from qraft.engine.base import ConnectionTestResult, Engine


class MySQLEngine(Engine):
    def __init__(self) -> None:
        self._conn: pymysql.Connection | None = None

    def connect(self, config: ConnectionConfig) -> None:
        connect_kwargs: dict = {
            "host": config.params.get("host", "localhost"),
            "port": int(config.params.get("port", "3306")),
            "database": config.params.get("database", ""),
            "user": config.params.get("user", "root"),
            "password": config.params.get("password", ""),
        }
        if "charset" in config.params:
            connect_kwargs["charset"] = config.params["charset"]
        if "ssl" in config.params:
            connect_kwargs["ssl"] = config.params["ssl"]

        self._conn = pymysql.connect(**connect_kwargs)

    def execute(self, sql: str) -> None:
        # PyMySQL doesn't support multi-statement by default,
        # so split on ';' and execute each statement separately.
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        with self._conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        self._conn.commit()

    def query(self, sql: str) -> list[tuple]:
        with self._conn.cursor() as cur:
            cur.execute(sql)
            return list(cur.fetchall())

    def create_schema(self, schema: str) -> None:
        # MySQL treats schemas as databases
        with self._conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS {schema}")
        self._conn.commit()

    def drop(self, target: str, kind: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(f"DROP {kind.upper()} IF EXISTS {target}")
        self._conn.commit()

    def object_exists(self, target: str) -> bool:
        parts = target.split(".")
        if len(parts) == 2:
            schema, name = parts
        else:
            schema, name = self._conn.db.decode(), parts[0]
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name = %s",
                (schema, name),
            )
            return cur.fetchone() is not None

    def test_connection(self) -> ConnectionTestResult:
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1")
            return ConnectionTestResult(
                success=True, details="MySQL connection OK"
            )
        except Exception as error:
            return ConnectionTestResult(success=False, details=str(error))

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
