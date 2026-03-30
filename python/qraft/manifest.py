import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from qraft import _core
from qraft.config.models import EnvConfig, Model


def generate_manifest(
    compiled_batches: list[list[_core.CompiledModel]],
    model_map: dict[str, Model],
    env: EnvConfig,
    dag: _core.DagHandle,
    batches: list[list[str]],
    project_name: str,
    target_dir: Path,
) -> dict:
    """Build manifest dict and write to target/manifest.json."""

    # Build parent_map and child_map from DAG edges
    edges = _core.dag_edges(dag)
    parent_map: dict[str, list[str]] = defaultdict(list)
    child_map: dict[str, list[str]] = defaultdict(list)
    for parent, child in edges:
        parent_map[child].append(parent)
        child_map[parent].append(child)

    # Add source references to parent_map
    for batch in compiled_batches:
        for compiled in batch:
            for source_name, table_name in compiled.sources:
                source_key = f"source:{source_name}.{table_name}"
                if source_key not in parent_map[compiled.name]:
                    parent_map[compiled.name].append(source_key)

    # Build nodes dict from compiled models
    nodes = {}
    for batch in compiled_batches:
        for compiled in batch:
            model = model_map.get(compiled.name)
            nodes[compiled.name] = {
                "name": compiled.name,
                "path": str(model.path) if model else f"{compiled.name}.sql",
                "raw_sql": model.raw_sql if model else "",
                "compiled_sql": compiled.compiled_sql,
                "ddl": compiled.ddl,
                "target": compiled.target,
                "materialization": compiled.materialization,
                "refs": compiled.refs,
                "sources": compiled.sources,
                "description": compiled.description,
                "tags": compiled.tags,
                "enabled": compiled.enabled,
            }

    # Build sources dict from env config
    sources = {}
    for source_name, src_config in env.sources.items():
        sources[source_name] = {
            "schema": src_config.schema,
            "database": src_config.database,
            "tables": src_config.tables,
        }

    manifest = {
        "metadata": {
            "project_name": project_name,
            "env": env.name,
            "schema": env.schema,
            "connection_type": env.connection.type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "nodes": nodes,
        "sources": sources,
        "parent_map": dict(parent_map),
        "child_map": dict(child_map),
        "batches": batches,
    }

    out_path = target_dir / "manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_manifest(target_dir: Path) -> dict:
    """Read manifest.json from target/."""
    return json.loads(
        (target_dir / "manifest.json").read_text(encoding="utf-8")
    )
