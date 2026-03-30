"""End-to-end macro integration tests."""

import pytest
from pathlib import Path

from qraft.compiler.bridge import compile_model
from qraft.compiler.macro_loader import MacroModuleNotFound, _module_cache
from qraft.config.loader import load
from qraft.config.models import Model
from qraft.config.resolver import resolve_env


@pytest.fixture(autouse=True)
def clear_cache():
    _module_cache.clear()
    yield
    _module_cache.clear()


@pytest.fixture
def project_with_macros(tmp_path):
    """Create a project with a macros/ directory."""
    (tmp_path / "project.yaml").write_text(
        "name: test_project\n"
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
        '  threshold: "100"\n'
        "environments:\n"
        "  local:\n"
        "  prod:\n"
        "    vars:\n"
        '      threshold: "500"\n'
    )
    (tmp_path / "models").mkdir()
    macros_dir = tmp_path / "macros"
    macros_dir.mkdir()
    (macros_dir / "common_transforms.py").write_text(
        "def safe_divide(numerator, denominator, vars):\n"
        "    return f'CASE WHEN {denominator} = 0 THEN NULL "
        "ELSE {numerator} / {denominator} END'\n"
        "\n"
        "def cents_to_dollars(amount, vars):\n"
        "    return f'({amount} / 100.0)'\n"
    )
    (macros_dir / "env_utils.py").write_text(
        "def above_threshold(col, vars):\n"
        "    return f'{col} > {vars[\"threshold\"]}'\n"
    )
    return tmp_path


class TestMacroIntegration:
    def test_model_without_macros_unchanged(self, project_with_macros):
        """Model without macros: key in front-matter compiles normally."""
        project = load(project_with_macros)
        env = resolve_env(project, "local")
        model = Model(
            name="plain",
            path=Path("plain.sql"),
            raw_sql="SELECT 1 AS id",
        )
        compiled = compile_model(model, env, project_root=project_with_macros)
        assert compiled.compiled_sql == "SELECT 1 AS id"

    def test_macro_expansion(self, project_with_macros):
        """Model with macros: [common_transforms] expands safe_divide."""
        project = load(project_with_macros)
        env = resolve_env(project, "local")
        model = Model(
            name="fct_orders",
            path=Path("fct_orders.sql"),
            raw_sql=(
                "---\nmacros: [common_transforms]\n---\n"
                "SELECT safe_divide(revenue, orders) AS avg_revenue FROM t"
            ),
        )
        compiled = compile_model(model, env, project_root=project_with_macros)
        assert "safe_divide" not in compiled.compiled_sql
        assert "CASE WHEN orders = 0 THEN NULL" in compiled.compiled_sql

    def test_unknown_macro_module_error(self, project_with_macros):
        """Missing macro module raises a clear error."""
        project = load(project_with_macros)
        env = resolve_env(project, "local")
        model = Model(
            name="bad_model",
            path=Path("bad_model.sql"),
            raw_sql=(
                "---\nmacros: [nonexistent_module]\n---\n"
                "SELECT 1"
            ),
        )
        with pytest.raises(MacroModuleNotFound, match="nonexistent_module"):
            compile_model(model, env, project_root=project_with_macros)

    def test_no_macros_front_matter_call_left_as_is(self, project_with_macros):
        """Without macros: in front-matter, function calls are native SQL."""
        project = load(project_with_macros)
        env = resolve_env(project, "local")
        model = Model(
            name="uses_native",
            path=Path("uses_native.sql"),
            raw_sql="SELECT safe_divide(a, b) FROM t",
        )
        compiled = compile_model(model, env, project_root=project_with_macros)
        assert "safe_divide(a, b)" in compiled.compiled_sql

    def test_nested_macro_calls(self, project_with_macros):
        """Nested calls expand correctly across iterations."""
        project = load(project_with_macros)
        env = resolve_env(project, "local")
        model = Model(
            name="nested",
            path=Path("nested.sql"),
            raw_sql=(
                "---\nmacros: [common_transforms]\n---\n"
                "SELECT safe_divide(cents_to_dollars(revenue), count) FROM t"
            ),
        )
        compiled = compile_model(model, env, project_root=project_with_macros)
        assert "safe_divide" not in compiled.compiled_sql
        assert "cents_to_dollars" not in compiled.compiled_sql
        assert "/ 100.0" in compiled.compiled_sql
        assert "CASE WHEN" in compiled.compiled_sql

    def test_multiple_modules(self, project_with_macros):
        """Functions from multiple modules are all available."""
        project = load(project_with_macros)
        env = resolve_env(project, "local")
        model = Model(
            name="multi",
            path=Path("multi.sql"),
            raw_sql=(
                "---\nmacros: [common_transforms, env_utils]\n---\n"
                "SELECT safe_divide(a, b) FROM t WHERE above_threshold(amount)"
            ),
        )
        compiled = compile_model(model, env, project_root=project_with_macros)
        assert "safe_divide" not in compiled.compiled_sql
        assert "above_threshold" not in compiled.compiled_sql
        assert "CASE WHEN" in compiled.compiled_sql
        assert "> 100" in compiled.compiled_sql

    def test_vars_differ_per_env(self, project_with_macros):
        """Macro receives different vars per environment."""
        project = load(project_with_macros)
        env_local = resolve_env(project, "local")
        env_prod = resolve_env(project, "prod")
        model = Model(
            name="env_model",
            path=Path("env_model.sql"),
            raw_sql=(
                "---\nmacros: [env_utils]\n---\n"
                "SELECT * FROM t WHERE above_threshold(amount)"
            ),
        )
        compiled_local = compile_model(
            model, env_local, project_root=project_with_macros
        )
        compiled_prod = compile_model(
            model, env_prod, project_root=project_with_macros
        )
        assert "> 100" in compiled_local.compiled_sql
        assert "> 500" in compiled_prod.compiled_sql

    def test_ddl_correct_after_expansion(self, project_with_macros):
        """DDL wraps the expanded SQL correctly."""
        project = load(project_with_macros)
        env = resolve_env(project, "local")
        model = Model(
            name="ddl_test",
            path=Path("ddl_test.sql"),
            raw_sql=(
                "---\nmacros: [common_transforms]\n---\n"
                "SELECT safe_divide(a, b) FROM t"
            ),
        )
        compiled = compile_model(model, env, project_root=project_with_macros)
        assert compiled.ddl.startswith("CREATE OR REPLACE VIEW")
        assert "CASE WHEN" in compiled.ddl
        assert "safe_divide" not in compiled.ddl

    def test_project_root_none_skips_macros(self, project_with_macros):
        """When project_root is None, macros are not expanded."""
        project = load(project_with_macros)
        env = resolve_env(project, "local")
        model = Model(
            name="no_root",
            path=Path("no_root.sql"),
            raw_sql=(
                "---\nmacros: [common_transforms]\n---\n"
                "SELECT safe_divide(a, b) FROM t"
            ),
        )
        compiled = compile_model(model, env, project_root=None)
        # Macros declared but not expanded without project_root
        assert "safe_divide(a, b)" in compiled.compiled_sql
