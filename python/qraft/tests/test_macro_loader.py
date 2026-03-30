"""Tests for macro_loader.load_macro_modules."""

import pytest
from pathlib import Path

from qraft.compiler.macro_loader import (
    MacroModuleNotFound,
    load_macro_modules,
    _module_cache,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the module cache before each test."""
    _module_cache.clear()
    yield
    _module_cache.clear()


@pytest.fixture
def macros_dir(tmp_path):
    """Create a macros/ directory with a sample module."""
    d = tmp_path / "macros"
    d.mkdir()
    (d / "common_transforms.py").write_text(
        "def safe_divide(numerator, denominator, vars):\n"
        "    return f'CASE WHEN {denominator} = 0 THEN NULL "
        "ELSE {numerator} / {denominator} END'\n"
        "\n"
        "def _private_helper():\n"
        "    pass\n"
    )
    return tmp_path


class TestLoadMacroModules:
    def test_loads_from_macros_dir(self, macros_dir):
        functions = load_macro_modules(["common_transforms"], macros_dir)
        assert "safe_divide" in functions
        assert callable(functions["safe_divide"])

    def test_skips_private_functions(self, macros_dir):
        functions = load_macro_modules(["common_transforms"], macros_dir)
        assert "_private_helper" not in functions

    def test_raises_for_missing_module(self, tmp_path):
        (tmp_path / "macros").mkdir()
        with pytest.raises(MacroModuleNotFound, match="nonexistent"):
            load_macro_modules(["nonexistent"], tmp_path)

    def test_falls_back_to_installed_package(self, tmp_path):
        (tmp_path / "macros").mkdir()
        # 'json' is a stdlib module
        functions = load_macro_modules(["json"], tmp_path)
        # json module has functions like loads, dumps
        assert len(functions) > 0

    def test_name_collision_first_wins(self, tmp_path):
        d = tmp_path / "macros"
        d.mkdir()
        (d / "a.py").write_text("def shared_fn(vars): return 'a'\n")
        (d / "b.py").write_text("def shared_fn(vars): return 'b'\n")
        functions = load_macro_modules(["a", "b"], tmp_path)
        assert functions["shared_fn"](vars={}) == "a"

    def test_multiple_modules(self, tmp_path):
        d = tmp_path / "macros"
        d.mkdir()
        (d / "mod1.py").write_text("def fn1(vars): return '1'\n")
        (d / "mod2.py").write_text("def fn2(vars): return '2'\n")
        functions = load_macro_modules(["mod1", "mod2"], tmp_path)
        assert "fn1" in functions
        assert "fn2" in functions
