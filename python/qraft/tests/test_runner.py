import pytest
from pathlib import Path

from qraft.config.loader import load
from qraft.config.models import ConnectionConfig
from qraft.config.resolver import resolve_env
from qraft.engine.duckdb_engine import DuckDBEngine
from qraft.runner.runner import run, write_compiled


@pytest.fixture
def engine(sample_project):
    db_path = str(sample_project / "test.duckdb")
    e = DuckDBEngine()
    e.connect(ConnectionConfig(type="duckdb", params={"path": db_path}))
    yield e
    e.close()


class TestRunner:
    def test_dry_run(self, sample_project, engine):
        project = load(sample_project)
        env = resolve_env(project, "local")
        results = run(
            models_dir=sample_project / "models",
            env=env,
            engine=engine,
            dry_run=True,
        )
        # Dry run returns empty list
        assert results == []

    def test_run_executes_models(self, sample_project, engine):
        """Test that run executes all models successfully.

        Note: source() references resolve to raw schema tables that don't
        exist in our in-memory DuckDB. We need models that don't use
        source() or we need to set up the source tables first.
        """
        # Create a simpler project without source() deps
        models_dir = sample_project / "models"
        # Overwrite with self-contained models
        (models_dir / "stg_orders.sql").write_text("SELECT 1 AS id, 100 AS amount")
        (models_dir / "stg_customers.sql").write_text("SELECT 1 AS id, 'Alice' AS name")
        (models_dir / "fct_revenue.sql").write_text(
            "SELECT o.amount FROM ref('stg_orders') o"
        )

        project = load(sample_project)
        env = resolve_env(project, "local")
        target_dir = sample_project / "target"
        results = run(
            models_dir=models_dir,
            env=env,
            engine=engine,
            target_dir=target_dir,
        )

        assert len(results) > 0
        all_models = [m for batch in results for m in batch.models]
        success_count = sum(1 for m in all_models if m.status == "success")
        assert success_count == 3

        # Verify compiled SQL was written
        compiled_dir = target_dir / "compiled" / "local"
        assert compiled_dir.exists()
        assert (compiled_dir / "stg_orders.sql").exists()
        assert (compiled_dir / "stg_customers.sql").exists()
        assert (compiled_dir / "fct_revenue.sql").exists()

    def test_run_with_select(self, sample_project, engine):
        models_dir = sample_project / "models"
        (models_dir / "stg_orders.sql").write_text("SELECT 1 AS id")
        (models_dir / "stg_customers.sql").write_text("SELECT 1 AS id")
        (models_dir / "fct_revenue.sql").write_text(
            "SELECT * FROM ref('stg_orders')"
        )

        project = load(sample_project)
        env = resolve_env(project, "local")
        results = run(
            models_dir=models_dir,
            env=env,
            engine=engine,
            select="stg_orders",
        )

        all_models = [m for batch in results for m in batch.models]
        assert len(all_models) == 1
        assert all_models[0].name == "stg_orders"
