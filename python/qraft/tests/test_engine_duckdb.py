import pytest

from qraft.config.models import ConnectionConfig
from qraft.engine.duckdb_engine import DuckDBEngine


@pytest.fixture
def engine():
    e = DuckDBEngine()
    e.connect(ConnectionConfig(type="duckdb", params={"path": ":memory:"}))
    yield e
    e.close()


class TestDuckDBEngine:
    def test_connect_and_test(self, engine):
        result = engine.test_connection()
        assert result.success is True
        assert "OK" in result.details

    def test_execute(self, engine):
        engine.execute("CREATE TABLE test_table (id INT, name VARCHAR)")
        engine.execute("INSERT INTO test_table VALUES (1, 'hello')")
        # Should not raise

    def test_create_schema(self, engine):
        engine.create_schema("analytics")
        # Verify schema exists by creating a table in it
        engine.execute("CREATE TABLE analytics.test (id INT)")

    def test_object_exists(self, engine):
        engine.execute("CREATE TABLE test_exists (id INT)")
        assert engine.object_exists("test_exists") is True
        assert engine.object_exists("nonexistent") is False

    def test_drop(self, engine):
        engine.execute("CREATE TABLE to_drop (id INT)")
        assert engine.object_exists("to_drop") is True
        engine.drop("to_drop", "table")
        assert engine.object_exists("to_drop") is False

    def test_close(self):
        e = DuckDBEngine()
        e.connect(ConnectionConfig(type="duckdb", params={"path": ":memory:"}))
        e.close()
        assert e._conn is None
