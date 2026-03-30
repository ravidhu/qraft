import json
from pathlib import Path

from qraft.compiler.bridge import compile_model
from qraft.config.loader import load
from qraft.config.resolver import resolve_env
from qraft.dag.bridge import build_dag, dag_edges, scan_models, topo_sort
from qraft.manifest import generate_manifest, load_manifest


def _setup_project(tmp_path):
    """Create a sample project and return (env, models, dag, batches, model_map)."""
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

    project = load(tmp_path)
    env = resolve_env(project, "local")
    models = scan_models(models_dir)
    dag = build_dag(models)
    batches = topo_sort(dag)
    model_map = {m.name: m for m in models}

    compiled_batches = []
    for batch in batches:
        compiled_batch = []
        for name in batch:
            model = model_map[name]
            compiled = compile_model(model, env, project_root=tmp_path)
            compiled_batch.append(compiled)
        compiled_batches.append(compiled_batch)

    return {
        "project_name": project.name,
        "env": env,
        "dag": dag,
        "batches": batches,
        "model_map": model_map,
        "compiled_batches": compiled_batches,
        "target_dir": tmp_path / "target",
    }


class TestManifest:
    def test_manifest_structure(self, tmp_path):
        """Manifest has all expected top-level keys."""
        ctx = _setup_project(tmp_path)
        manifest = generate_manifest(
            compiled_batches=ctx["compiled_batches"],
            model_map=ctx["model_map"],
            env=ctx["env"],
            dag=ctx["dag"],
            batches=ctx["batches"],
            project_name=ctx["project_name"],
            target_dir=ctx["target_dir"],
        )

        assert set(manifest.keys()) == {
            "metadata",
            "nodes",
            "sources",
            "parent_map",
            "child_map",
            "batches",
        }
        assert manifest["metadata"]["project_name"] == "test_project"
        assert manifest["metadata"]["env"] == "local"
        assert manifest["metadata"]["schema"] == "analytics"
        assert manifest["metadata"]["connection_type"] == "duckdb"
        assert "generated_at" in manifest["metadata"]

    def test_manifest_nodes(self, tmp_path):
        """Each compiled model appears in nodes with correct fields."""
        ctx = _setup_project(tmp_path)
        manifest = generate_manifest(
            compiled_batches=ctx["compiled_batches"],
            model_map=ctx["model_map"],
            env=ctx["env"],
            dag=ctx["dag"],
            batches=ctx["batches"],
            project_name=ctx["project_name"],
            target_dir=ctx["target_dir"],
        )

        nodes = manifest["nodes"]
        assert set(nodes.keys()) == {
            "stg_orders",
            "stg_customers",
            "fct_revenue",
        }

        stg = nodes["stg_orders"]
        assert stg["name"] == "stg_orders"
        assert stg["target"] == "analytics.stg_orders"
        assert stg["materialization"] == "view"
        assert "compiled_sql" in stg
        assert "ddl" in stg
        assert "raw_sql" in stg
        assert stg["path"] == "stg_orders.sql"

        fct = nodes["fct_revenue"]
        assert set(fct["refs"]) == {"stg_orders", "stg_customers"}

    def test_manifest_parent_child_maps(self, tmp_path):
        """parent_map and child_map reflect the DAG correctly."""
        ctx = _setup_project(tmp_path)
        manifest = generate_manifest(
            compiled_batches=ctx["compiled_batches"],
            model_map=ctx["model_map"],
            env=ctx["env"],
            dag=ctx["dag"],
            batches=ctx["batches"],
            project_name=ctx["project_name"],
            target_dir=ctx["target_dir"],
        )

        parent_map = manifest["parent_map"]
        child_map = manifest["child_map"]

        # fct_revenue depends on stg_orders and stg_customers
        assert "stg_orders" in parent_map["fct_revenue"]
        assert "stg_customers" in parent_map["fct_revenue"]

        # stg_orders and stg_customers feed into fct_revenue
        assert "fct_revenue" in child_map["stg_orders"]
        assert "fct_revenue" in child_map["stg_customers"]

        # stg_orders depends on source:raw.orders
        assert "source:raw.orders" in parent_map["stg_orders"]

        # stg_customers depends on source:raw.customers
        assert "source:raw.customers" in parent_map["stg_customers"]

    def test_manifest_sources(self, tmp_path):
        """Sources from env config appear in manifest."""
        ctx = _setup_project(tmp_path)
        manifest = generate_manifest(
            compiled_batches=ctx["compiled_batches"],
            model_map=ctx["model_map"],
            env=ctx["env"],
            dag=ctx["dag"],
            batches=ctx["batches"],
            project_name=ctx["project_name"],
            target_dir=ctx["target_dir"],
        )

        assert "raw" in manifest["sources"]
        raw = manifest["sources"]["raw"]
        assert raw["schema"] == "main"
        assert "orders" in raw["tables"]
        assert "customers" in raw["tables"]

    def test_manifest_batches(self, tmp_path):
        """Batches match topological sort output."""
        ctx = _setup_project(tmp_path)
        manifest = generate_manifest(
            compiled_batches=ctx["compiled_batches"],
            model_map=ctx["model_map"],
            env=ctx["env"],
            dag=ctx["dag"],
            batches=ctx["batches"],
            project_name=ctx["project_name"],
            target_dir=ctx["target_dir"],
        )

        batches = manifest["batches"]
        assert len(batches) == 2
        # First batch: staging models (no inter-dependencies)
        assert set(batches[0]) == {"stg_orders", "stg_customers"}
        # Second batch: fct_revenue (depends on staging)
        assert batches[1] == ["fct_revenue"]

    def test_manifest_roundtrip(self, tmp_path):
        """Generate then load produces equivalent data."""
        ctx = _setup_project(tmp_path)
        original = generate_manifest(
            compiled_batches=ctx["compiled_batches"],
            model_map=ctx["model_map"],
            env=ctx["env"],
            dag=ctx["dag"],
            batches=ctx["batches"],
            project_name=ctx["project_name"],
            target_dir=ctx["target_dir"],
        )

        loaded = load_manifest(ctx["target_dir"])

        assert loaded["metadata"]["project_name"] == original["metadata"]["project_name"]
        assert loaded["nodes"].keys() == original["nodes"].keys()
        assert loaded["parent_map"] == original["parent_map"]
        assert loaded["child_map"] == original["child_map"]
        assert loaded["batches"] == original["batches"]

    def test_manifest_file_written(self, tmp_path):
        """manifest.json is written to target_dir."""
        ctx = _setup_project(tmp_path)
        generate_manifest(
            compiled_batches=ctx["compiled_batches"],
            model_map=ctx["model_map"],
            env=ctx["env"],
            dag=ctx["dag"],
            batches=ctx["batches"],
            project_name=ctx["project_name"],
            target_dir=ctx["target_dir"],
        )

        manifest_path = ctx["target_dir"] / "manifest.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert data["metadata"]["project_name"] == "test_project"


class TestDagEdges:
    def test_dag_edges_returns_tuples(self, tmp_path):
        """dag_edges returns (parent, child) tuples."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "a.sql").write_text("SELECT 1 AS id")
        (models_dir / "b.sql").write_text(
            "SELECT * FROM ref('a')"
        )
        (models_dir / "c.sql").write_text(
            "SELECT * FROM ref('a') JOIN ref('b') ON TRUE"
        )

        models = scan_models(models_dir)
        dag = build_dag(models)
        edges = dag_edges(dag)

        # a -> b, a -> c, b -> c
        assert ("a", "b") in edges
        assert ("a", "c") in edges
        assert ("b", "c") in edges
        assert len(edges) == 3
