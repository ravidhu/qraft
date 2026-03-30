import os
from pathlib import Path

import pytest

from qraft.utils.env import load_env, resolve_env_vars


class TestResolveEnvVars:
    def test_resolve_string(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "localhost")
        result = resolve_env_vars("host=${DB_HOST}")
        assert result == "host=localhost"

    def test_resolve_nested_dict(self, monkeypatch):
        monkeypatch.setenv("USER", "admin")
        data = {"connection": {"user": "${USER}"}}
        result = resolve_env_vars(data)
        assert result["connection"]["user"] == "admin"

    def test_resolve_list(self, monkeypatch):
        monkeypatch.setenv("VAL", "x")
        result = resolve_env_vars(["${VAL}", "plain"])
        assert result == ["x", "plain"]

    def test_missing_env_var_raises(self):
        with pytest.raises(ValueError, match="NONEXISTENT_VAR_12345"):
            resolve_env_vars("${NONEXISTENT_VAR_12345}")

    def test_no_vars_passthrough(self):
        assert resolve_env_vars("plain string") == "plain string"
        assert resolve_env_vars(42) == 42
        assert resolve_env_vars(None) is None

    def test_multiple_vars_in_string(self, monkeypatch):
        monkeypatch.setenv("HOST", "db.local")
        monkeypatch.setenv("PORT", "5432")
        result = resolve_env_vars("${HOST}:${PORT}")
        assert result == "db.local:5432"


class TestLoadEnv:
    def test_loads_env_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("TEST_QRAFT_VAR=hello\n")
        load_env(tmp_path)
        assert os.environ.get("TEST_QRAFT_VAR") == "hello"
        # Cleanup
        monkeypatch.delenv("TEST_QRAFT_VAR", raising=False)

    def test_no_env_file_is_fine(self, tmp_path):
        load_env(tmp_path)  # Should not raise
