"""Tests for macro_expander.expand."""

import pytest
from pathlib import Path

from qraft.compiler.macro_expander import (
    MacroArgumentError,
    MacroExpansionError,
    MacroExpansionLoop,
    expand,
)
from qraft.compiler.macro_loader import _module_cache


@pytest.fixture(autouse=True)
def clear_cache():
    _module_cache.clear()
    yield
    _module_cache.clear()


@pytest.fixture
def project_with_macros(tmp_path):
    d = tmp_path / "macros"
    d.mkdir()
    (d / "common_transforms.py").write_text(
        "def safe_divide(numerator, denominator, vars):\n"
        "    return f'CASE WHEN {denominator} = 0 THEN NULL "
        "ELSE {numerator} / {denominator} END'\n"
        "\n"
        "def cents_to_dollars(amount, vars):\n"
        "    return f'({amount} / 100.0)'\n"
    )
    return tmp_path


class TestExpand:
    def test_simple_expansion(self, project_with_macros):
        sql = "SELECT safe_divide(a, b) FROM t"
        result = expand(
            sql=sql,
            macros_list=["common_transforms"],
            vars={},
            model_name="test",
            project_root=project_with_macros,
        )
        assert "CASE WHEN b = 0 THEN NULL ELSE a / b END" in result
        assert "safe_divide" not in result

    def test_multiple_calls(self, tmp_path):
        d = tmp_path / "macros"
        d.mkdir()
        (d / "ops.py").write_text(
            "def double(x, vars):\n"
            "    return f'({x} * 2)'\n"
            "def negate(x, vars):\n"
            "    return f'(-{x})'\n"
        )
        result = expand(
            sql="SELECT double(a), negate(b)",
            macros_list=["ops"],
            vars={},
            model_name="test",
            project_root=tmp_path,
        )
        assert "(a * 2)" in result
        assert "(-b)" in result

    def test_nested_calls(self, project_with_macros):
        # cents_to_dollars(x) expands first, then safe_divide gets expanded
        sql = "SELECT safe_divide(cents_to_dollars(revenue), count)"
        result = expand(
            sql=sql,
            macros_list=["common_transforms"],
            vars={},
            model_name="test",
            project_root=project_with_macros,
        )
        assert "safe_divide" not in result
        assert "cents_to_dollars" not in result
        assert "/ 100.0" in result

    def test_no_macro_calls_unchanged(self, project_with_macros):
        sql = "SELECT a / b FROM t"
        result = expand(
            sql=sql,
            macros_list=["common_transforms"],
            vars={},
            model_name="test",
            project_root=project_with_macros,
        )
        assert result == sql

    def test_argument_count_mismatch(self, project_with_macros):
        with pytest.raises(MacroArgumentError, match="expects 2 arguments, got 1"):
            expand(
                sql="SELECT safe_divide(a)",
                macros_list=["common_transforms"],
                vars={},
                model_name="fct_orders",
                project_root=project_with_macros,
            )

    def test_function_raises_error(self, tmp_path):
        d = tmp_path / "macros"
        d.mkdir()
        (d / "bad.py").write_text(
            "def broken(x, vars):\n"
            "    raise RuntimeError('something went wrong')\n"
        )
        with pytest.raises(MacroExpansionError, match="RuntimeError"):
            expand(
                sql="SELECT broken(a)",
                macros_list=["bad"],
                vars={},
                model_name="test",
                project_root=tmp_path,
            )

    def test_function_returns_non_string(self, tmp_path):
        d = tmp_path / "macros"
        d.mkdir()
        (d / "bad.py").write_text(
            "def bad_return(x, vars):\n"
            "    return 42\n"
        )
        with pytest.raises(MacroExpansionError, match="must return a string, got int"):
            expand(
                sql="SELECT bad_return(a)",
                macros_list=["bad"],
                vars={},
                model_name="test",
                project_root=tmp_path,
            )

    def test_vars_passed_to_function(self, tmp_path):
        d = tmp_path / "macros"
        d.mkdir()
        (d / "env_aware.py").write_text(
            "def use_var(col, vars):\n"
            "    return f'{col} > {vars[\"threshold\"]}'\n"
        )
        result = expand(
            sql="SELECT * FROM t WHERE use_var(amount)",
            macros_list=["env_aware"],
            vars={"threshold": "100"},
            model_name="test",
            project_root=tmp_path,
        )
        assert "amount > 100" in result

    def test_max_iterations_loop(self, tmp_path):
        d = tmp_path / "macros"
        d.mkdir()
        # Function that produces another call to itself
        (d / "loop.py").write_text(
            "def loop_fn(x, vars):\n"
            "    return f'loop_fn({x})'\n"
        )
        with pytest.raises(MacroExpansionLoop, match="exceeded 100 iterations"):
            expand(
                sql="SELECT loop_fn(a)",
                macros_list=["loop"],
                vars={},
                model_name="test",
                project_root=tmp_path,
            )

    def test_error_includes_model_name(self, project_with_macros):
        with pytest.raises(MacroArgumentError, match="fct_orders"):
            expand(
                sql="SELECT safe_divide(a)",
                macros_list=["common_transforms"],
                vars={},
                model_name="fct_orders",
                project_root=project_with_macros,
            )

    def test_error_includes_function_name(self, project_with_macros):
        with pytest.raises(MacroArgumentError, match="safe_divide"):
            expand(
                sql="SELECT safe_divide(a)",
                macros_list=["common_transforms"],
                vars={},
                model_name="test",
                project_root=project_with_macros,
            )

    def test_unclosed_paren_in_sql(self, project_with_macros):
        """Rust parser should raise error for unclosed parenthesis."""
        with pytest.raises(ValueError, match="Unclosed parenthesis"):
            expand(
                sql="SELECT safe_divide(a, b",
                macros_list=["common_transforms"],
                vars={},
                model_name="test",
                project_root=project_with_macros,
            )
