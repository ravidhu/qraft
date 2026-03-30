import pytest
from pathlib import Path


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal project structure for testing."""
    db_path = str(tmp_path / "test.duckdb")
    (tmp_path / "project.yaml").write_text(
        "name: test_project\n"
        "connection:\n"
        "  type: duckdb\n"
        f"  path: {db_path}\n"
        "schema: analytics\n"
        "materialization: view\n"
        "sources:\n"
        "  raw:\n"
        "    schema: main\n"
        "    tables:\n"
        "      - orders\n"
        "      - customers\n"
        "vars:\n"
        '  min_amount: "0"\n'
        "environments:\n"
        "  local:\n"
        "  prod:\n"
        "    schema: analytics_prod\n"
        "    vars:\n"
        '      min_amount: "100"\n'
    )

    models_dir = tmp_path / "models"
    models_dir.mkdir()

    (models_dir / "stg_orders.sql").write_text(
        "SELECT * FROM source('raw', 'orders') "
        "WHERE amount > {{ min_amount }}"
    )
    (models_dir / "stg_customers.sql").write_text(
        "SELECT * FROM source('raw', 'customers')"
    )
    (models_dir / "fct_revenue.sql").write_text(
        "SELECT SUM(amount) AS total "
        "FROM ref('stg_orders') o "
        "JOIN ref('stg_customers') c ON o.customer_id = c.id"
    )

    return tmp_path


@pytest.fixture
def models_dir(sample_project):
    return sample_project / "models"


def _make_project(tmp_path: Path, connection_type: str) -> Path:
    """Create a minimal project structure with a given connection type."""
    (tmp_path / "project.yaml").write_text(
        "name: test_project\n"
        "connection:\n"
        f"  type: {connection_type}\n"
        "schema: analytics\n"
        "materialization: view\n"
        "sources:\n"
        "  raw:\n"
        "    schema: main\n"
        "    tables:\n"
        "      - orders\n"
        "vars: {}\n"
        "environments:\n"
        "  local:\n"
    )
    (tmp_path / "models").mkdir(exist_ok=True)
    return tmp_path


@pytest.fixture
def postgres_project(tmp_path):
    return _make_project(tmp_path, "postgres")


@pytest.fixture
def mysql_project(tmp_path):
    return _make_project(tmp_path, "mysql")


@pytest.fixture
def trino_project(tmp_path):
    return _make_project(tmp_path, "trino")
