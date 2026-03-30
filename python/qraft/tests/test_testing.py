import json
import os

import pytest
from click.testing import CliRunner

from qraft.config.models import ConnectionConfig, Model
from qraft.engine.duckdb_engine import DuckDBEngine
from qraft.testing.discovery import discover_tests, _extract_yaml_front_matter
from qraft.testing.generic import generate_test_sql
from qraft.testing.models import DataTestDefinition, DataTestResult
from qraft.testing.results import write_test_results
from qraft.testing.runner import run_tests


# ─────────────────────────────────
# Fixtures
# ─────────────────────────────────


@pytest.fixture
def engine():
    e = DuckDBEngine()
    e.connect(ConnectionConfig(type="duckdb", params={"path": ":memory:"}))
    e.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    yield e
    e.close()


@pytest.fixture
def seeded_engine(engine):
    """Engine with test data pre-loaded."""
    engine.execute(
        "CREATE TABLE analytics.orders AS "
        "SELECT * FROM (VALUES "
        "(1, 'pending', 100, 1), "
        "(2, 'shipped', 200, 2), "
        "(3, 'delivered', 50, 1), "
        "(4, 'pending', NULL, 3)"
        ") AS t(id, status, amount, customer_id)"
    )
    engine.execute(
        "CREATE TABLE analytics.customers AS "
        "SELECT * FROM (VALUES "
        "(1, 'Alice'), "
        "(2, 'Bob'), "
        "(3, 'Charlie')"
        ") AS t(id, name)"
    )
    return engine


# ─────────────────────────────────
# Front-matter parsing
# ─────────────────────────────────


class TestFrontMatterParsing:
    def test_no_front_matter(self):
        assert _extract_yaml_front_matter("SELECT 1") is None

    def test_simple_front_matter(self):
        sql = "---\nmaterialization: table\n---\nSELECT 1"
        fm = _extract_yaml_front_matter(sql)
        assert fm["materialization"] == "table"

    def test_columns_block(self):
        sql = (
            "---\n"
            "materialization: table\n"
            "columns:\n"
            "  order_id:\n"
            "    description: Primary key\n"
            "    tests: [unique, not_null]\n"
            "  status:\n"
            "    tests:\n"
            "      - accepted_values:\n"
            "          values: [pending, shipped]\n"
            "---\n"
            "SELECT 1"
        )
        fm = _extract_yaml_front_matter(sql)
        assert "columns" in fm
        assert "order_id" in fm["columns"]
        assert fm["columns"]["order_id"]["description"] == "Primary key"
        assert fm["columns"]["order_id"]["tests"] == ["unique", "not_null"]


# ─────────────────────────────────
# Test discovery
# ─────────────────────────────────


class TestDiscovery:
    def test_discover_simple_tests(self):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql=(
                "---\n"
                "columns:\n"
                "  id:\n"
                "    tests: [unique, not_null]\n"
                "---\n"
                "SELECT 1"
            ),
        )
        tests = discover_tests([model])
        assert len(tests) == 2
        assert tests[0].model_name == "orders"
        assert tests[0].column == "id"
        assert tests[0].test_type == "unique"
        assert tests[1].test_type == "not_null"

    def test_discover_parameterized_test(self):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql=(
                "---\n"
                "columns:\n"
                "  status:\n"
                "    tests:\n"
                "      - accepted_values:\n"
                "          values: [a, b, c]\n"
                "---\n"
                "SELECT 1"
            ),
        )
        tests = discover_tests([model])
        assert len(tests) == 1
        assert tests[0].test_type == "accepted_values"
        assert tests[0].params["values"] == ["a", "b", "c"]

    def test_discover_with_severity(self):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql=(
                "---\n"
                "columns:\n"
                "  id:\n"
                "    tests:\n"
                "      - unique:\n"
                "          severity: warn\n"
                "---\n"
                "SELECT 1"
            ),
        )
        tests = discover_tests([model])
        assert len(tests) == 1
        assert tests[0].severity == "warn"

    def test_discover_with_where(self):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql=(
                "---\n"
                "columns:\n"
                "  id:\n"
                "    tests:\n"
                "      - unique:\n"
                "          where: status != 'deleted'\n"
                "---\n"
                "SELECT 1"
            ),
        )
        tests = discover_tests([model])
        assert tests[0].where == "status != 'deleted'"

    def test_discover_no_tests(self):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql="SELECT 1",
        )
        tests = discover_tests([model])
        assert len(tests) == 0

    def test_discover_description_only(self):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql=(
                "---\n"
                "columns:\n"
                "  id:\n"
                "    description: Primary key\n"
                "---\n"
                "SELECT 1"
            ),
        )
        tests = discover_tests([model])
        assert len(tests) == 0

    def test_discover_relationships(self):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql=(
                "---\n"
                "columns:\n"
                "  customer_id:\n"
                "    tests:\n"
                "      - relationships:\n"
                "          to: ref('customers')\n"
                "          field: id\n"
                "---\n"
                "SELECT 1"
            ),
        )
        tests = discover_tests([model])
        assert len(tests) == 1
        assert tests[0].test_type == "relationships"
        assert tests[0].params["to"] == "ref('customers')"
        assert tests[0].params["field"] == "id"


# ─────────────────────────────────
# SQL generation
# ─────────────────────────────────


class TestSQLGeneration:
    def test_not_null(self):
        test = DataTestDefinition(
            model_name="orders", column="id", test_type="not_null"
        )
        sql = generate_test_sql(test, "analytics.orders")
        assert "IS NULL" in sql
        assert "analytics.orders" in sql

    def test_unique(self):
        test = DataTestDefinition(
            model_name="orders", column="id", test_type="unique"
        )
        sql = generate_test_sql(test, "analytics.orders")
        assert "GROUP BY" in sql
        assert "HAVING COUNT(*) > 1" in sql

    def test_accepted_values(self):
        test = DataTestDefinition(
            model_name="orders",
            column="status",
            test_type="accepted_values",
            params={"values": ["pending", "shipped"]},
        )
        sql = generate_test_sql(test, "analytics.orders")
        assert "NOT IN" in sql
        assert "'pending'" in sql
        assert "'shipped'" in sql

    def test_relationships(self):
        test = DataTestDefinition(
            model_name="orders",
            column="customer_id",
            test_type="relationships",
            params={"to": "ref('customers')", "field": "id"},
        )
        sql = generate_test_sql(test, "analytics.orders")
        assert "analytics.customers" in sql
        assert "NOT IN" in sql

    def test_number_of_rows(self):
        test = DataTestDefinition(
            model_name="orders",
            column="_",
            test_type="number_of_rows",
            params={"min": 10},
        )
        sql = generate_test_sql(test, "analytics.orders")
        assert "COUNT(*)" in sql
        assert "10" in sql

    def test_accepted_range(self):
        test = DataTestDefinition(
            model_name="orders",
            column="amount",
            test_type="accepted_range",
            params={"min": 0, "max": 1000},
        )
        sql = generate_test_sql(test, "analytics.orders")
        assert "amount < 0" in sql
        assert "amount > 1000" in sql

    def test_unique_combination(self):
        test = DataTestDefinition(
            model_name="orders",
            column="_",
            test_type="unique_combination_of_columns",
            params={"columns": ["id", "status"]},
        )
        sql = generate_test_sql(test, "analytics.orders")
        assert "id, status" in sql
        assert "GROUP BY" in sql

    def test_unknown_test_type(self):
        test = DataTestDefinition(
            model_name="orders", column="id", test_type="bogus"
        )
        with pytest.raises(ValueError, match="Unknown test type"):
            generate_test_sql(test, "analytics.orders")

    def test_where_clause(self):
        test = DataTestDefinition(
            model_name="orders",
            column="id",
            test_type="not_null",
            where="status != 'deleted'",
        )
        sql = generate_test_sql(test, "analytics.orders")
        assert "_qraft_filtered" in sql
        assert "status != 'deleted'" in sql


# ─────────────────────────────────
# Test execution (DuckDB integration)
# ─────────────────────────────────


class TestExecution:
    def test_not_null_passes(self, seeded_engine):
        test = DataTestDefinition(
            model_name="orders", column="id", test_type="not_null"
        )
        sql = generate_test_sql(test, "analytics.orders")
        rows = seeded_engine.query(
            f"SELECT * FROM ({sql}) t LIMIT 10"
        )
        assert len(rows) == 0

    def test_not_null_fails(self, seeded_engine):
        test = DataTestDefinition(
            model_name="orders", column="amount", test_type="not_null"
        )
        sql = generate_test_sql(test, "analytics.orders")
        rows = seeded_engine.query(
            f"SELECT * FROM ({sql}) t LIMIT 10"
        )
        assert len(rows) == 1  # row 4 has NULL amount

    def test_unique_passes(self, seeded_engine):
        test = DataTestDefinition(
            model_name="orders", column="id", test_type="unique"
        )
        sql = generate_test_sql(test, "analytics.orders")
        rows = seeded_engine.query(
            f"SELECT * FROM ({sql}) t LIMIT 10"
        )
        assert len(rows) == 0

    def test_unique_fails(self, seeded_engine):
        test = DataTestDefinition(
            model_name="orders",
            column="customer_id",
            test_type="unique",
        )
        sql = generate_test_sql(test, "analytics.orders")
        rows = seeded_engine.query(
            f"SELECT * FROM ({sql}) t LIMIT 10"
        )
        assert len(rows) == 1  # customer_id=1 appears twice

    def test_accepted_values_passes(self, seeded_engine):
        test = DataTestDefinition(
            model_name="orders",
            column="status",
            test_type="accepted_values",
            params={"values": ["pending", "shipped", "delivered"]},
        )
        sql = generate_test_sql(test, "analytics.orders")
        rows = seeded_engine.query(
            f"SELECT * FROM ({sql}) t LIMIT 10"
        )
        assert len(rows) == 0

    def test_accepted_values_fails(self, seeded_engine):
        test = DataTestDefinition(
            model_name="orders",
            column="status",
            test_type="accepted_values",
            params={"values": ["pending", "shipped"]},
        )
        sql = generate_test_sql(test, "analytics.orders")
        rows = seeded_engine.query(
            f"SELECT * FROM ({sql}) t LIMIT 10"
        )
        assert len(rows) == 1  # "delivered" not in list

    def test_relationships_passes(self, seeded_engine):
        test = DataTestDefinition(
            model_name="orders",
            column="customer_id",
            test_type="relationships",
            params={"to": "ref('customers')", "field": "id"},
        )
        sql = generate_test_sql(test, "analytics.orders")
        rows = seeded_engine.query(
            f"SELECT * FROM ({sql}) t LIMIT 10"
        )
        assert len(rows) == 0

    def test_relationships_fails(self, seeded_engine):
        # Add a row with an orphan customer_id
        seeded_engine.execute(
            "INSERT INTO analytics.orders VALUES (5, 'pending', 300, 99)"
        )
        test = DataTestDefinition(
            model_name="orders",
            column="customer_id",
            test_type="relationships",
            params={"to": "ref('customers')", "field": "id"},
        )
        sql = generate_test_sql(test, "analytics.orders")
        rows = seeded_engine.query(
            f"SELECT * FROM ({sql}) t LIMIT 10"
        )
        assert len(rows) == 1

    def test_number_of_rows_passes(self, seeded_engine):
        test = DataTestDefinition(
            model_name="orders",
            column="_",
            test_type="number_of_rows",
            params={"min": 3},
        )
        sql = generate_test_sql(test, "analytics.orders")
        rows = seeded_engine.query(
            f"SELECT * FROM ({sql}) t LIMIT 10"
        )
        assert len(rows) == 0

    def test_number_of_rows_fails(self, seeded_engine):
        test = DataTestDefinition(
            model_name="orders",
            column="_",
            test_type="number_of_rows",
            params={"min": 100},
        )
        sql = generate_test_sql(test, "analytics.orders")
        rows = seeded_engine.query(
            f"SELECT * FROM ({sql}) t LIMIT 10"
        )
        assert len(rows) == 1


# ─────────────────────────────────
# Runner integration
# ─────────────────────────────────


class TestRunner:
    def test_run_tests_all_pass(self, seeded_engine):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql=(
                "---\n"
                "columns:\n"
                "  id:\n"
                "    tests: [unique, not_null]\n"
                "---\n"
                "SELECT 1"
            ),
        )
        results = run_tests(
            models=[model],
            engine=seeded_engine,
            schema="analytics",
        )
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_run_tests_with_failure(self, seeded_engine):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql=(
                "---\n"
                "columns:\n"
                "  amount:\n"
                "    tests: [not_null]\n"
                "---\n"
                "SELECT 1"
            ),
        )
        results = run_tests(
            models=[model],
            engine=seeded_engine,
            schema="analytics",
        )
        assert len(results) == 1
        assert not results[0].passed
        assert results[0].failures_count >= 1

    def test_run_tests_no_tests(self, seeded_engine):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql="SELECT 1",
        )
        results = run_tests(
            models=[model],
            engine=seeded_engine,
            schema="analytics",
        )
        assert len(results) == 0

    def test_run_tests_warn_severity(self, seeded_engine):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql=(
                "---\n"
                "columns:\n"
                "  amount:\n"
                "    tests:\n"
                "      - not_null:\n"
                "          severity: warn\n"
                "---\n"
                "SELECT 1"
            ),
        )
        results = run_tests(
            models=[model],
            engine=seeded_engine,
            schema="analytics",
        )
        assert len(results) == 1
        assert not results[0].passed
        assert results[0].test.severity == "warn"

    def test_run_tests_fail_fast(self, seeded_engine):
        model = Model(
            name="orders",
            path="orders.sql",
            raw_sql=(
                "---\n"
                "columns:\n"
                "  amount:\n"
                "    tests: [not_null, unique]\n"
                "---\n"
                "SELECT 1"
            ),
        )
        results = run_tests(
            models=[model],
            engine=seeded_engine,
            schema="analytics",
            fail_fast=True,
        )
        # Should stop after first failure (not_null on amount fails)
        assert len(results) == 1
        assert not results[0].passed


# ─────────────────────────────────
# Test results JSON output
# ─────────────────────────────────


class TestResults:
    def test_write_all_passing(self, tmp_path):
        results = [
            DataTestResult(
                test=DataTestDefinition(
                    model_name="orders", column="id", test_type="not_null"
                ),
                passed=True,
                failures_count=0,
                failures_sample=[],
            ),
            DataTestResult(
                test=DataTestDefinition(
                    model_name="orders", column="id", test_type="unique"
                ),
                passed=True,
                failures_count=0,
                failures_sample=[],
            ),
        ]
        out = write_test_results(results, "local", "analytics", tmp_path)
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["summary"]["total"] == 2
        assert data["summary"]["passed"] == 2
        assert data["summary"]["failed"] == 0
        assert len(data["results"]) == 2
        assert all(r["passed"] for r in data["results"])

    def test_write_with_failures(self, tmp_path):
        results = [
            DataTestResult(
                test=DataTestDefinition(
                    model_name="orders", column="amount", test_type="not_null"
                ),
                passed=False,
                failures_count=2,
                failures_sample=[(4, None), (5, None)],
            ),
        ]
        out = write_test_results(results, "local", "analytics", tmp_path)
        data = json.loads(out.read_text())
        assert data["summary"]["failed"] == 1
        assert data["results"][0]["failures_count"] == 2
        assert len(data["results"][0]["failures_sample"]) == 2

    def test_write_with_warnings(self, tmp_path):
        results = [
            DataTestResult(
                test=DataTestDefinition(
                    model_name="orders",
                    column="amount",
                    test_type="not_null",
                    severity="warn",
                ),
                passed=False,
                failures_count=1,
                failures_sample=[(4, None)],
            ),
        ]
        out = write_test_results(results, "local", "analytics", tmp_path)
        data = json.loads(out.read_text())
        assert data["summary"]["warned"] == 1
        assert data["summary"]["failed"] == 0

    def test_write_with_error(self, tmp_path):
        results = [
            DataTestResult(
                test=DataTestDefinition(
                    model_name="orders", column="id", test_type="bogus"
                ),
                passed=False,
                failures_count=0,
                failures_sample=[],
                error="Unknown test type: 'bogus'",
            ),
        ]
        out = write_test_results(results, "local", "analytics", tmp_path)
        data = json.loads(out.read_text())
        assert data["summary"]["errored"] == 1
        assert data["results"][0]["error"] == "Unknown test type: 'bogus'"

    def test_write_metadata(self, tmp_path):
        results = [
            DataTestResult(
                test=DataTestDefinition(
                    model_name="orders", column="id", test_type="not_null"
                ),
                passed=True,
                failures_count=0,
                failures_sample=[],
            ),
        ]
        out = write_test_results(results, "staging", "analytics_stg", tmp_path)
        data = json.loads(out.read_text())
        assert data["metadata"]["env"] == "staging"
        assert data["metadata"]["schema"] == "analytics_stg"
        assert "generated_at" in data["metadata"]

    def test_write_includes_params(self, tmp_path):
        results = [
            DataTestResult(
                test=DataTestDefinition(
                    model_name="orders",
                    column="status",
                    test_type="accepted_values",
                    params={"values": ["a", "b"]},
                ),
                passed=True,
                failures_count=0,
                failures_sample=[],
            ),
        ]
        out = write_test_results(results, "local", "analytics", tmp_path)
        data = json.loads(out.read_text())
        assert data["results"][0]["params"] == {"values": ["a", "b"]}


# ─────────────────────────────────
# CLI integration
# ─────────────────────────────────


class TestCLI:
    def test_test_command_no_tests(self, sample_project):
        from qraft.cli import main

        runner = CliRunner()
        os.chdir(sample_project)
        result = runner.invoke(main, ["test", "--env", "local"])
        assert result.exit_code == 0
        assert "No tests found" in result.output

    def test_test_command_with_tests(self, tmp_path):
        from qraft.cli import main

        db_path = str(tmp_path / "test.duckdb")
        (tmp_path / "project.yaml").write_text(
            "name: test_project\n"
            "connection:\n"
            "  type: duckdb\n"
            f"  path: {db_path}\n"
            "schema: analytics\n"
            "materialization: table\n"
            "sources: {}\n"
            "vars: {}\n"
            "environments:\n"
            "  local:\n"
        )
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "test_model.sql").write_text(
            "---\n"
            "columns:\n"
            "  id:\n"
            "    tests: [unique, not_null]\n"
            "---\n"
            "SELECT 1 AS id UNION ALL SELECT 2 AS id"
        )

        runner = CliRunner()
        os.chdir(tmp_path)

        # First run to materialize
        run_result = runner.invoke(main, ["run", "--env", "local"])
        assert run_result.exit_code == 0

        # Then test
        result = runner.invoke(main, ["test", "--env", "local"])
        assert result.exit_code == 0
        assert "PASS" in result.output

        # Verify test_results.json was written
        results_file = tmp_path / "target" / "test_results.json"
        assert results_file.exists()
        data = json.loads(results_file.read_text())
        assert data["summary"]["passed"] == 2
        assert data["metadata"]["env"] == "local"

    def test_build_command(self, tmp_path):
        from qraft.cli import main

        db_path = str(tmp_path / "test.duckdb")
        (tmp_path / "project.yaml").write_text(
            "name: test_project\n"
            "connection:\n"
            "  type: duckdb\n"
            f"  path: {db_path}\n"
            "schema: analytics\n"
            "materialization: table\n"
            "sources: {}\n"
            "vars: {}\n"
            "environments:\n"
            "  local:\n"
        )
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "test_model.sql").write_text(
            "---\n"
            "columns:\n"
            "  id:\n"
            "    tests: [not_null]\n"
            "---\n"
            "SELECT 1 AS id"
        )

        runner = CliRunner()
        os.chdir(tmp_path)

        result = runner.invoke(main, ["build", "--env", "local"])
        assert result.exit_code == 0
        assert "PASS" in result.output
