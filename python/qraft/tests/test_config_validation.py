from pathlib import Path

import pytest

from qraft.config.loader import ConfigValidationError, load


def _write_yaml(tmp_path: Path, content: str) -> Path:
    (tmp_path / "project.yaml").write_text(content)
    return tmp_path


class TestConfigValidation:
    def test_missing_name(self, tmp_path):
        _write_yaml(tmp_path, "connection:\n  type: duckdb\n")
        with pytest.raises(ConfigValidationError, match="'name' is required"):
            load(tmp_path)

    def test_missing_connection(self, tmp_path):
        _write_yaml(tmp_path, "name: test\n")
        with pytest.raises(ConfigValidationError, match="'connection' is required"):
            load(tmp_path)

    def test_missing_connection_type(self, tmp_path):
        _write_yaml(tmp_path, "name: test\nconnection:\n  path: test.db\n")
        with pytest.raises(ConfigValidationError, match="'connection.type' is required"):
            load(tmp_path)

    def test_unknown_engine_type_loads_successfully(self, tmp_path):
        """Unknown engine types should be allowed — they fail at runtime, not config time."""
        _write_yaml(
            tmp_path,
            "name: test\nconnection:\n  type: snowflake\nschema: public\n"
            "environments:\n  local:\n",
        )
        project = load(tmp_path)
        assert project.connection.type == "snowflake"

    def test_invalid_materialization(self, tmp_path):
        _write_yaml(
            tmp_path,
            "name: test\nconnection:\n  type: duckdb\n"
            "materialization: snapshot\n"
            "environments:\n  local:\n",
        )
        with pytest.raises(ConfigValidationError, match="snapshot"):
            load(tmp_path)

    def test_invalid_sources_type(self, tmp_path):
        _write_yaml(
            tmp_path,
            "name: test\nconnection:\n  type: duckdb\n"
            "sources: not_a_dict\n"
            "environments:\n  local:\n",
        )
        with pytest.raises(ConfigValidationError, match="'sources' must be a mapping"):
            load(tmp_path)

    def test_invalid_vars_type(self, tmp_path):
        _write_yaml(
            tmp_path,
            "name: test\nconnection:\n  type: duckdb\n"
            "vars: [a, b]\n"
            "environments:\n  local:\n",
        )
        with pytest.raises(ConfigValidationError, match="'vars' must be a mapping"):
            load(tmp_path)

    def test_invalid_env_materialization(self, tmp_path):
        _write_yaml(
            tmp_path,
            "name: test\nconnection:\n  type: duckdb\n"
            "environments:\n  prod:\n    materialization: invalid\n",
        )
        with pytest.raises(ConfigValidationError, match="prod.*materialization"):
            load(tmp_path)

    def test_unknown_env_engine_type_loads_successfully(self, tmp_path):
        """Unknown engine types in environments should be allowed."""
        _write_yaml(
            tmp_path,
            "name: test\nconnection:\n  type: duckdb\n"
            "environments:\n  prod:\n    connection:\n      type: bigquery\n",
        )
        project = load(tmp_path)
        assert project.environments["prod"]["connection"]["type"] == "bigquery"

    def test_valid_config_passes(self, tmp_path):
        _write_yaml(
            tmp_path,
            "name: test\n"
            "connection:\n  type: duckdb\n  path: test.db\n"
            "schema: analytics\n"
            "materialization: view\n"
            "sources:\n  raw:\n    schema: main\n    tables:\n      - orders\n"
            "vars:\n  min: '0'\n"
            "environments:\n  local:\n",
        )
        project = load(tmp_path)
        assert project.name == "test"
        assert project.connection.type == "duckdb"

    def test_empty_environment_is_valid(self, tmp_path):
        _write_yaml(
            tmp_path,
            "name: test\nconnection:\n  type: duckdb\n"
            "environments:\n  local:\n",
        )
        project = load(tmp_path)
        assert "local" in project.environments

    def test_multiple_errors_reported(self, tmp_path):
        _write_yaml(tmp_path, "connection: not_a_dict\n")
        with pytest.raises(ConfigValidationError) as exc_info:
            load(tmp_path)
        msg = str(exc_info.value)
        assert "'name' is required" in msg
        assert "'connection' is required" in msg
