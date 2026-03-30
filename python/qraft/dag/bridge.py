from pathlib import Path

from qraft import _core
from qraft.config.models import Model


def scan_models(models_dir: Path) -> list[Model]:
    """Recursively scan the models directory for ``.sql`` files.

    Walks ``models_dir`` recursively, reads each ``.sql`` file, and returns a
    list of :class:`Model` objects with the filename stem as the model name.

    Args:
        models_dir: Path to the ``models/`` directory.

    Returns:
        Sorted list of Model objects (sorted by file path).
    """
    models = []
    for sql_file in sorted(models_dir.rglob("*.sql")):
        name = sql_file.stem
        raw_sql = sql_file.read_text(encoding="utf-8")
        models.append(
            Model(
                name=name,
                path=sql_file.relative_to(models_dir),
                raw_sql=raw_sql,
            )
        )
    return models


def build_dag(models: list[Model]) -> _core.DagHandle:
    """Parse SQL files and build a dependency graph.

    Each model becomes a node. Each ``ref()`` call creates a directed edge
    from the dependency to the dependent model.

    Args:
        models: List of scanned models with raw SQL.

    Returns:
        An opaque DAG handle for use with other DAG functions.
    """
    parsed_models = []
    for model in models:
        parsed = _core.parse_sql(model.raw_sql)
        parsed_models.append(
            _core.ParsedModel(
                name=model.name,
                refs=parsed.refs,
                sources=parsed.sources,
            )
        )
    return _core.build_dag(parsed_models)


def validate_dag(
    dag: _core.DagHandle,
    models: list[Model],
    available_sources: list[str],
) -> list[_core.ValidationError]:
    """Validate the DAG for missing refs, undeclared sources, and cycles.

    Uses fuzzy matching (Jaro-Winkler) to suggest corrections for typos.

    Args:
        dag: DAG handle from :func:`build_dag` or :func:`build_pipeline`.
        models: List of scanned models.
        available_sources: Source names declared in ``project.yaml``.

    Returns:
        List of validation errors (empty if the DAG is valid).
    """
    parsed_models = []
    for model in models:
        parsed = _core.parse_sql(model.raw_sql)
        parsed_models.append(
            _core.ParsedModel(
                name=model.name,
                refs=parsed.refs,
                sources=parsed.sources,
            )
        )
    return _core.validate_dag(dag, parsed_models, available_sources)


def topo_sort(dag: _core.DagHandle) -> list[list[str]]:
    """Topologically sort the DAG into parallelizable execution batches.

    Uses Kahn's algorithm. Models within the same batch have no
    interdependencies and can execute concurrently.

    Args:
        dag: DAG handle.

    Returns:
        List of batches, where each batch is a list of model names.
    """
    return _core.topo_sort(dag)


def select_models(dag: _core.DagHandle, pattern: str) -> list[str]:
    """Select models matching a dbt-style pattern.

    Supported patterns: ``model_name``, ``model+``, ``+model``, ``+model+``,
    ``tag:name``, ``prefix*``.

    Args:
        dag: DAG handle.
        pattern: Selection pattern string.

    Returns:
        List of matching model names.
    """
    return _core.select_models(dag, pattern)


def dag_edges(dag: _core.DagHandle) -> list[tuple[str, str]]:
    """Return all dependency edges in the DAG.

    Args:
        dag: DAG handle.

    Returns:
        List of ``(parent, child)`` tuples representing dependency edges.
    """
    return _core.dag_edges(dag)


def build_pipeline(
    models: list[Model],
    available_sources: list[str],
    select: str | None = None,
) -> tuple[
    _core.DagHandle,
    list[list[str]],
    list[_core.ParsedModel],
    list[_core.ValidationError],
]:
    """Run the full DAG pipeline in a single Rust call.

    Performs: parse SQL → build graph → validate → topological sort → apply
    ``--select`` filter. This is more efficient than calling each step
    individually because all work happens in Rust with no intermediate
    Python↔Rust serialization.

    Args:
        models: List of scanned models with raw SQL.
        available_sources: Source names declared in ``project.yaml``.
        select: Optional selection pattern to filter the output batches.

    Returns:
        A 4-tuple of:
        - **dag** — Opaque DAG handle
        - **batches** — Topologically sorted execution batches (filtered if select given)
        - **parsed_models** — Parsed model metadata (refs, sources, tags)
        - **errors** — Validation errors (empty if valid)
    """
    raw_models = [(model.name, model.raw_sql) for model in models]
    return _core.build_pipeline(raw_models, available_sources, select=select)
