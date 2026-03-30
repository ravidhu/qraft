from pathlib import Path

from qraft.compiler.bridge import compile_model
from qraft.config.loader import load
from qraft.config.models import ConnectionConfig, Model
from qraft.config.resolver import resolve_env
from qraft.dag.bridge import build_dag, scan_models, topo_sort
from qraft.engine.duckdb_engine import DuckDBEngine
from qraft.runner.runner import run


class TestIntegration:
    def test_full_pipeline(self, tmp_path):
        """End-to-end: config → scan → DAG → compile → verify."""
        (tmp_path / "project.yaml").write_text(
            "name: test\n"
            "connection:\n"
            "  type: duckdb\n"
            '  path: ":memory:"\n'
            "schema: analytics\n"
            "materialization: view\n"
            "sources:\n"
            "  raw:\n"
            "    schema: main\n"
            "    tables:\n"
            "      - orders\n"
            "vars:\n"
            '  min_amount: "0"\n'
            "environments:\n"
            "  local:\n"
        )
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "stg_orders.sql").write_text(
            "SELECT * FROM source('raw', 'orders') "
            "WHERE amount > {{ min_amount }}"
        )
        (models_dir / "fct_revenue.sql").write_text(
            "SELECT SUM(amount) FROM ref('stg_orders')"
        )

        # Load and resolve
        project = load(tmp_path)
        env = resolve_env(project, "local")

        # Scan and build DAG
        models = scan_models(models_dir)
        dag = build_dag(models)
        batches = topo_sort(dag)

        # Verify ordering
        assert len(batches) == 2
        assert batches[0] == ["stg_orders"]
        assert batches[1] == ["fct_revenue"]

        # Compile
        model = next(m for m in models if m.name == "fct_revenue")
        compiled = compile_model(model, env)
        assert "analytics.stg_orders" in compiled.compiled_sql
        assert compiled.target == "analytics.fct_revenue"

    def test_full_execution(self, tmp_path):
        """End-to-end: config → scan → DAG → compile → execute on DuckDB."""
        db_path = str(tmp_path / "test.duckdb")
        (tmp_path / "project.yaml").write_text(
            "name: test\n"
            "connection:\n"
            "  type: duckdb\n"
            f"  path: {db_path}\n"
            "schema: analytics\n"
            "materialization: view\n"
            "sources: {}\n"
            "vars: {}\n"
            "environments:\n"
            "  local:\n"
        )
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "base.sql").write_text(
            "SELECT 1 AS id, 100 AS amount"
        )
        (models_dir / "summary.sql").write_text(
            "SELECT SUM(amount) AS total FROM ref('base')"
        )

        project = load(tmp_path)
        env = resolve_env(project, "local")

        engine = DuckDBEngine()
        engine.connect(env.connection)

        try:
            results = run(
                models_dir=models_dir,
                env=env,
                engine=engine,
            )

            all_models = [
                m for batch in results for m in batch.models
            ]
            assert all(m.status == "success" for m in all_models)
            assert len(all_models) == 2

            # Verify the view was actually created
            # Re-connect to read from the same file the workers wrote to
            engine.close()
            engine.connect(env.connection)
            assert engine.object_exists("analytics.base")
            assert engine.object_exists("analytics.summary")
        finally:
            engine.close()
