from abc import ABC, abstractmethod
from dataclasses import dataclass

from qraft.config.models import ConnectionConfig


@dataclass
class ConnectionTestResult:
    """Result of a database connection test.

    Attributes:
        success: Whether the connection test succeeded.
        details: Human-readable description (e.g. engine name and target).
    """

    success: bool
    details: str


class Engine(ABC):
    """Abstract base class for database engines.

    Each engine implementation handles a specific database backend (DuckDB,
    PostgreSQL, MySQL, Trino). The runner creates one engine per worker process
    and calls :meth:`connect` before any SQL execution.

    To add a new engine:

    1. Create ``python/qraft/engine/<name>_engine.py``
    2. Subclass :class:`Engine` and implement all abstract methods
    3. Register it in :func:`qraft.engine.get_engine`
    4. Add the client library as an optional dependency in ``pyproject.toml``
    """

    @abstractmethod
    def connect(self, config: ConnectionConfig) -> None:
        """Open a connection to the database.

        Args:
            config: Connection configuration with engine type and params.
        """

    @abstractmethod
    def execute(self, sql: str) -> None:
        """Execute one or more DDL/DML statements.

        Multi-statement SQL (semicolon-separated) should be handled by the
        implementation — some drivers support it natively, others need splitting.

        Args:
            sql: The SQL string to execute.
        """

    @abstractmethod
    def query(self, sql: str) -> list[tuple]:
        """Execute a SELECT statement and return all rows.

        Args:
            sql: The SELECT query to execute.

        Returns:
            List of tuples, one per row.
        """

    @abstractmethod
    def create_schema(self, schema: str) -> None:
        """Create a schema if it does not already exist.

        Args:
            schema: Schema name to create.
        """

    @abstractmethod
    def drop(self, target: str, kind: str) -> None:
        """Drop a database object (table or view) if it exists.

        Args:
            target: Fully qualified object name (e.g. ``schema.model``).
            kind: The materialization type (``view``, ``table``, etc.).
        """

    @abstractmethod
    def object_exists(self, target: str) -> bool:
        """Check whether a table or view exists in the database.

        Args:
            target: Fully qualified object name (e.g. ``schema.model``).

        Returns:
            True if the object exists, False otherwise.
        """

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """Test the current database connection.

        Returns:
            A :class:`ConnectionTestResult` with success status and details.
        """

    @abstractmethod
    def close(self) -> None:
        """Close the database connection and release resources."""
