import pytest

from qraft.compiler.bridge import batch_compile, compile_model, parse_sql
from qraft.config.loader import load
from qraft.config.models import Model
from qraft.config.resolver import resolve_env
from pathlib import Path


class TestParseSql:
    def test_parse_refs(self):
        parsed = parse_sql("SELECT * FROM ref('stg_orders')")
        assert parsed.refs == ["stg_orders"]

    def test_parse_sources(self):
        parsed = parse_sql("SELECT * FROM source('raw', 'orders')")
        assert parsed.sources == [("raw", "orders")]

    def test_parse_variables(self):
        parsed = parse_sql(
            "SELECT * FROM {{ schema }}.t WHERE x > {{ min_amount }}"
        )
        assert parsed.variables == ["schema", "min_amount"]

    def test_parse_front_matter(self):
        parsed = parse_sql(
            "---\nmaterialization: table\n---\nSELECT 1"
        )
        assert parsed.front_matter["materialization"] == "table"


class TestCompileModel:
    def test_compile_resolves_refs(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "local")
        model = Model(
            name="fct_revenue",
            path=Path("fct_revenue.sql"),
            raw_sql="SELECT * FROM ref('stg_orders')",
        )
        compiled = compile_model(model, env)
        assert "analytics.stg_orders" in compiled.compiled_sql
        assert compiled.target == "analytics.fct_revenue"

    def test_compile_resolves_sources(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "local")
        model = Model(
            name="stg_orders",
            path=Path("stg_orders.sql"),
            raw_sql="SELECT * FROM source('raw', 'orders')",
        )
        compiled = compile_model(model, env)
        assert "main.orders" in compiled.compiled_sql

    def test_compile_resolves_vars(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "local")
        model = Model(
            name="test",
            path=Path("test.sql"),
            raw_sql="SELECT * FROM {{ schema }}.t WHERE x > {{ min_amount }}",
        )
        compiled = compile_model(model, env)
        assert "analytics.t" in compiled.compiled_sql
        assert "> 0" in compiled.compiled_sql

    def test_compile_generates_ddl_view(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "local")
        model = Model(
            name="test",
            path=Path("test.sql"),
            raw_sql="SELECT 1",
        )
        compiled = compile_model(model, env)
        assert compiled.ddl.startswith("CREATE OR REPLACE VIEW")
        assert compiled.materialization == "view"

    def test_front_matter_overrides_materialization(self, sample_project):
        """Front-matter materialization should override the env default."""
        project = load(sample_project)
        env = resolve_env(project, "local")
        assert env.materialization == "view"  # env default is view
        model = Model(
            name="heavy_table",
            path=Path("heavy_table.sql"),
            raw_sql="---\nmaterialization: table\n---\nSELECT 1",
        )
        compiled = compile_model(model, env)
        assert compiled.materialization == "table"
        assert "CREATE TABLE" in compiled.ddl
        assert "CREATE OR REPLACE VIEW" not in compiled.ddl


class TestBatchCompile:
    def test_batch_compile_basic(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "local")
        models = [
            Model(
                name="stg_orders",
                path=Path("stg_orders.sql"),
                raw_sql="SELECT * FROM source('raw', 'orders')",
            ),
            Model(
                name="fct_revenue",
                path=Path("fct_revenue.sql"),
                raw_sql="SELECT * FROM ref('stg_orders')",
            ),
        ]
        compiled = batch_compile(models, env)
        assert len(compiled) == 2
        assert "main.orders" in compiled[0].compiled_sql
        assert "analytics.stg_orders" in compiled[1].compiled_sql

    def test_batch_compile_matches_single(self, sample_project):
        """batch_compile should produce same results as individual compile_model."""
        project = load(sample_project)
        env = resolve_env(project, "local")
        models = [
            Model(
                name="test_a",
                path=Path("test_a.sql"),
                raw_sql="SELECT 1",
            ),
            Model(
                name="test_b",
                path=Path("test_b.sql"),
                raw_sql="---\nmaterialization: table\n---\nSELECT 2",
            ),
        ]
        batch_results = batch_compile(models, env)
        single_results = [compile_model(m, env) for m in models]

        for batch_r, single_r in zip(batch_results, single_results):
            assert batch_r.name == single_r.name
            assert batch_r.ddl == single_r.ddl
            assert batch_r.compiled_sql == single_r.compiled_sql
            assert batch_r.materialization == single_r.materialization

    def test_batch_compile_preserves_order(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "local")
        models = [
            Model(name=f"model_{i}", path=Path(f"model_{i}.sql"), raw_sql=f"SELECT {i}")
            for i in range(5)
        ]
        compiled = batch_compile(models, env)
        assert [c.name for c in compiled] == [f"model_{i}" for i in range(5)]

    def test_batch_compile_front_matter_override(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "local")
        models = [
            Model(
                name="view_model",
                path=Path("view_model.sql"),
                raw_sql="SELECT 1",
            ),
            Model(
                name="table_model",
                path=Path("table_model.sql"),
                raw_sql="---\nmaterialization: table\n---\nSELECT 2",
            ),
        ]
        compiled = batch_compile(models, env)
        assert compiled[0].materialization == "view"
        assert compiled[1].materialization == "table"
        assert "CREATE OR REPLACE VIEW" in compiled[0].ddl
        assert "CREATE TABLE" in compiled[1].ddl


class TestMaterializationValidation:
    """Engine-specific materialization validation."""

    _MAT_VIEW_SQL = (
        "---\nmaterialization: materialized_view\n---\nSELECT 1"
    )

    def test_materialized_view_allowed_on_postgres(self, postgres_project):
        project = load(postgres_project)
        env = resolve_env(project, "local")
        model = Model(
            name="mv_test",
            path=Path("mv_test.sql"),
            raw_sql=self._MAT_VIEW_SQL,
        )
        compiled = compile_model(model, env)
        assert compiled.materialization == "materialized_view"
        assert "CREATE MATERIALIZED VIEW" in compiled.ddl

    def test_materialized_view_allowed_on_trino(self, trino_project):
        project = load(trino_project)
        env = resolve_env(project, "local")
        model = Model(
            name="mv_test",
            path=Path("mv_test.sql"),
            raw_sql=self._MAT_VIEW_SQL,
        )
        compiled = compile_model(model, env)
        assert compiled.materialization == "materialized_view"

    def test_materialized_view_rejected_on_mysql(self, mysql_project):
        project = load(mysql_project)
        env = resolve_env(project, "local")
        model = Model(
            name="mv_test",
            path=Path("mv_test.sql"),
            raw_sql=self._MAT_VIEW_SQL,
        )
        with pytest.raises(ValueError, match="not supported by engine 'mysql'"):
            compile_model(model, env)

    def test_materialized_view_rejected_on_duckdb(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "local")
        model = Model(
            name="mv_test",
            path=Path("mv_test.sql"),
            raw_sql=self._MAT_VIEW_SQL,
        )
        with pytest.raises(
            ValueError, match="not supported by engine 'duckdb'"
        ):
            compile_model(model, env)

    def test_unknown_engine_passes_validation(self, tmp_path):
        """Unknown engines should not be blocked — they may support anything."""
        from qraft.tests.conftest import _make_project

        project_dir = _make_project(tmp_path, "snowflake")
        project = load(project_dir)
        env = resolve_env(project, "local")
        model = Model(
            name="mv_test",
            path=Path("mv_test.sql"),
            raw_sql=self._MAT_VIEW_SQL,
        )
        compiled = compile_model(model, env)
        assert compiled.materialization == "materialized_view"
