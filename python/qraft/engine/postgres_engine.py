import psycopg

from qraft.config.models import ConnectionConfig
from qraft.engine.base import ConnectionTestResult, Engine


class PostgresEngine(Engine):
    def __init__(self) -> None:
        self._conn: psycopg.Connection | None = None

    def connect(self, config: ConnectionConfig) -> None:
        # Accept both "database" and "dbname" for the database parameter
        dbname = config.params.get("database", config.params.get("dbname", "postgres"))
        connect_kwargs: dict = {
            "host": config.params.get("host", "localhost"),
            "port": int(config.params.get("port", "5432")),
            "dbname": dbname,
            "user": config.params.get("user", "postgres"),
            "password": config.params.get("password", ""),
            "autocommit": False,
        }
        if "sslmode" in config.params:
            connect_kwargs["sslmode"] = config.params["sslmode"]

        self._conn = psycopg.connect(**connect_kwargs)

    def execute(self, sql: str) -> None:
        # Split multi-statement DDL (e.g., DROP + CREATE TABLE AS)
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        with self._conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        self._conn.commit()

    def query(self, sql: str) -> list[tuple]:
        with self._conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()

    def create_schema(self, schema: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        self._conn.commit()

    def drop(self, target: str, kind: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(f"DROP {kind.upper()} IF EXISTS {target} CASCADE")
        self._conn.commit()

    def object_exists(self, target: str) -> bool:
        parts = target.split(".")
        if len(parts) == 2:
            schema, name = parts
        else:
            schema, name = "public", parts[0]
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
                success=True, details="PostgreSQL connection OK"
            )
        except Exception as error:
            return ConnectionTestResult(success=False, details=str(error))

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
