import os

import pytest
from click.testing import CliRunner

from qraft.cli import main
from qraft.compiler.macro_loader import _module_cache


class TestCLI:
    def test_init(self, tmp_path):
        runner = CliRunner()
        os.chdir(tmp_path)
        result = runner.invoke(main, ["init", "my_project"])
        assert result.exit_code == 0
        assert (tmp_path / "my_project" / "project.yaml").exists()
        assert (tmp_path / "my_project" / "models").is_dir()
        assert (tmp_path / "my_project" / "macros").is_dir()
        assert (
            tmp_path / "my_project" / "models" / "example.sql"
        ).exists()

    def test_validate_ok(self, sample_project):
        runner = CliRunner()
        os.chdir(sample_project)
        result = runner.invoke(main, ["validate", "--env", "local"])
        assert result.exit_code == 0
        assert "All checks passed" in result.output

    def test_validate_bad_env(self, sample_project):
        runner = CliRunner()
        os.chdir(sample_project)
        result = runner.invoke(main, ["validate", "--env", "staging"])
        assert result.exit_code != 0

    def test_compile(self, sample_project):
        runner = CliRunner()
        os.chdir(sample_project)
        result = runner.invoke(main, ["compile", "--env", "local"])
        assert result.exit_code == 0
        # Should show compiled SQL for all models
        assert "stg_orders" in result.output
        # Verify compiled SQL was written to target/
        compiled_dir = sample_project / "target" / "compiled" / "local"
        assert compiled_dir.exists()
        sql_files = list(compiled_dir.rglob("*.sql"))
        assert len(sql_files) == 3

    def test_dag(self, sample_project):
        runner = CliRunner()
        os.chdir(sample_project)
        result = runner.invoke(main, ["dag"])
        assert result.exit_code == 0
        assert "3 models" in result.output

    def test_test_connection(self, sample_project):
        runner = CliRunner()
        os.chdir(sample_project)
        result = runner.invoke(
            main, ["test-connection", "--env", "local"]
        )
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_run_dry(self, sample_project):
        runner = CliRunner()
        os.chdir(sample_project)
        result = runner.invoke(
            main, ["run", "--env", "local", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Would execute" in result.output

    def test_show_compiled(self, sample_project):
        runner = CliRunner()
        os.chdir(sample_project)
        result = runner.invoke(
            main, ["show", "--env", "local", "stg_orders"]
        )
        assert result.exit_code == 0
        assert "main.orders" in result.output

    def test_show_unknown_model(self, sample_project):
        runner = CliRunner()
        os.chdir(sample_project)
        result = runner.invoke(
            main, ["show", "--env", "local", "nonexistent"]
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_show_expanded(self, sample_project):
        _module_cache.clear()
        # Add macros dir and a model with macros
        macros_dir = sample_project / "macros"
        macros_dir.mkdir(exist_ok=True)
        (macros_dir / "transforms.py").write_text(
            "def double(x, vars):\n"
            "    return f'({x} * 2)'\n"
        )
        (sample_project / "models" / "macro_test.sql").write_text(
            "---\nmacros: [transforms]\n---\n"
            "SELECT double(amount) FROM source('raw', 'orders')"
        )
        runner = CliRunner()
        os.chdir(sample_project)
        result = runner.invoke(
            main, ["show", "--env", "local", "--expanded", "macro_test"]
        )
        assert result.exit_code == 0
        assert "after macro expansion" in result.output
        assert "(amount * 2)" in result.output
        assert "main.orders" in result.output
        assert "double(" not in result.output.split("expansion)")[-1]
        _module_cache.clear()
