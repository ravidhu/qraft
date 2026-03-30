from pathlib import Path

import pytest

from qraft.config.loader import load
from qraft.config.resolver import resolve_env


class TestLoader:
    def test_load_project(self, sample_project):
        project = load(sample_project)
        assert project.name == "test_project"
        assert project.connection.type == "duckdb"
        assert project.schema == "analytics"
        assert project.materialization == "view"
        assert "raw" in project.sources
        assert project.sources["raw"].schema == "main"
        assert "orders" in project.sources["raw"].tables

    def test_load_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load(tmp_path)

    def test_load_vars(self, sample_project):
        project = load(sample_project)
        assert project.vars["min_amount"] == "0"

    def test_load_environments(self, sample_project):
        project = load(sample_project)
        assert "local" in project.environments
        assert "prod" in project.environments


class TestResolver:
    def test_resolve_local(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "local")
        assert env.name == "local"
        assert env.schema == "analytics"
        assert env.vars["min_amount"] == "0"
        assert env.connection.type == "duckdb"

    def test_resolve_prod_overrides(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "prod")
        assert env.schema == "analytics_prod"
        assert env.vars["min_amount"] == "100"

    def test_resolve_unknown_env(self, sample_project):
        project = load(sample_project)
        with pytest.raises(ValueError, match="not found"):
            resolve_env(project, "staging")

    def test_sources_preserved(self, sample_project):
        project = load(sample_project)
        env = resolve_env(project, "local")
        assert "raw" in env.sources
        assert env.sources["raw"].schema == "main"
