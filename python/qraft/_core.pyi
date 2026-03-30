"""Type stubs for the compiled Rust extension module ``qraft._core``.

This module is built from ``rust/src/`` via PyO3 and maturin. The stubs
provide IDE autocompletion and type checking for the Python-facing API.
"""

from __future__ import annotations

# ── Data Classes ──────────────────────────────────────────────────


class ParsedSQL:
    """Result of parsing a raw SQL file."""

    refs: list[str]
    """Model names referenced via ``ref('...')``."""
    sources: list[tuple[str, str]]
    """Source references as ``(source_name, table_name)`` tuples."""
    variables: list[str]
    """Variable names referenced via ``{{ ... }}``."""
    body: str
    """SQL body with front-matter stripped."""
    front_matter: dict[str, str] | None
    """Parsed YAML front-matter key-value pairs, or None if absent."""


class CompiledModel:
    """Fully compiled model ready for database execution."""

    name: str
    """Model name (filename without ``.sql``)."""
    compiled_sql: str
    """Resolved SQL body (refs, sources, vars replaced; macros expanded)."""
    ddl: str
    """Complete DDL statement (e.g. ``CREATE OR REPLACE VIEW ... AS ...``)."""
    target: str
    """Fully qualified target name (e.g. ``analytics.stg_orders``)."""
    materialization: str
    """Effective materialization type."""
    refs: list[str]
    """Model names this model depends on."""
    sources: list[tuple[str, str]]
    """Source references as ``(source_name, table_name)`` tuples."""
    description: str | None
    """Model description from front-matter."""
    tags: list[str]
    """Tags from front-matter."""
    enabled: bool
    """Whether the model is enabled (default True)."""


class ResolvedModel:
    """Intermediate compilation result — resolved but not yet wrapped in DDL."""

    name: str
    resolved_sql: str
    """SQL with refs, sources, and variables resolved."""
    target: str
    materialization: str
    refs: list[str]
    sources: list[tuple[str, str]]
    macros: list[str]
    """Macro module names declared in front-matter."""
    description: str | None
    tags: list[str]
    enabled: bool
    unique_key: str | None
    """Column used for upsert in ``table_incremental`` materialization."""


class SourceInfo:
    """Source database/schema info passed from Python config to Rust compiler."""

    database: str
    """Database/catalog name (empty string if not applicable)."""
    schema: str
    """Schema name where source tables reside."""

    def __init__(self, database: str, schema: str) -> None: ...


class ParsedModel:
    """Minimal parsed model used for DAG construction."""

    name: str
    refs: list[str]
    sources: list[tuple[str, str]]
    tags: list[str]
    materialization: str | None

    def __init__(
        self,
        name: str,
        refs: list[str],
        sources: list[tuple[str, str]],
        tags: list[str] = ...,
        materialization: str | None = None,
    ) -> None: ...


class EphemeralModel:
    """Ephemeral model info for CTE injection during compilation."""

    name: str
    compiled_body: str
    """Resolved SQL body to be injected as a CTE."""
    deps: list[str]
    """Model names this ephemeral depends on."""

    def __init__(self, name: str, compiled_body: str, deps: list[str]) -> None: ...


class DagHandle:
    """Opaque handle to the internal petgraph DAG.

    This object is created by :func:`build_dag` or :func:`build_pipeline`
    and passed back to other DAG functions. It cannot be inspected from Python.
    """

    ...


class ValidationError:
    """DAG validation error with optional fix suggestion."""

    model: str
    """Model that has the error."""
    error_type: str
    """Error category: ``"missing_ref"``, ``"missing_source"``, or ``"cycle"``."""
    message: str
    """Human-readable error description."""
    suggestion: str | None
    """Suggested fix (e.g. closest matching model name)."""


class MacroCall:
    """A macro function call found in SQL text."""

    name: str
    """Function name."""
    args: list[str]
    """Parsed argument strings."""
    start: int
    """Byte offset of the call start in the SQL string."""
    end: int
    """Byte offset of the call end in the SQL string."""


# ── Functions ─────────────────────────────────────────────────────


def parse_sql(raw_sql: str) -> ParsedSQL:
    """Parse a raw SQL file and extract refs, sources, variables, and front-matter."""
    ...


def compile_model(
    raw_sql: str,
    model_name: str,
    schema: str,
    materialization: str,
    vars: dict[str, str],
    sources: dict[str, SourceInfo],
    ephemerals: dict[str, EphemeralModel] = ...,
) -> CompiledModel:
    """Full single-model compilation: resolve refs/sources/vars and generate DDL."""
    ...


def resolve_model(
    raw_sql: str,
    model_name: str,
    schema: str,
    materialization: str,
    vars: dict[str, str],
    sources: dict[str, SourceInfo],
    ephemerals: dict[str, EphemeralModel] = ...,
) -> ResolvedModel:
    """Phase 1: resolve refs, sources, and variables without generating DDL."""
    ...


def wrap_ddl(
    resolved: ResolvedModel,
    resolved_sql: str | None = None,
) -> CompiledModel:
    """Phase 2: wrap resolved SQL in DDL based on materialization type.

    If *resolved_sql* is provided, it overrides the SQL from the ResolvedModel
    (used when macros have modified the SQL).
    """
    ...


def find_macro_calls(
    sql: str,
    known_functions: list[str],
) -> list[MacroCall]:
    """Find macro function calls in SQL text matching known function names."""
    ...


def build_dag(models: list[ParsedModel]) -> DagHandle:
    """Build a directed acyclic graph from parsed models."""
    ...


def validate_dag(
    dag: DagHandle,
    models: list[ParsedModel],
    available_sources: list[str],
) -> list[ValidationError]:
    """Validate the DAG: detect cycles, missing refs, and undeclared sources."""
    ...


def topo_sort(dag: DagHandle) -> list[list[str]]:
    """Topologically sort the DAG into parallelizable execution batches."""
    ...


def dag_edges(dag: DagHandle) -> list[tuple[str, str]]:
    """Return all DAG edges as ``(parent, child)`` tuples."""
    ...


def build_pipeline(
    raw_models: list[tuple[str, str]],
    available_sources: list[str],
    select: str | None = None,
) -> tuple[DagHandle, list[list[str]], list[ParsedModel], list[ValidationError]]:
    """Consolidated DAG pipeline: parse, build, validate, sort, and optionally select.

    Returns:
        A 4-tuple of ``(dag, batches, parsed_models, errors)``.
    """
    ...


def batch_resolve(
    raw_models: list[tuple[str, str]],
    schema: str,
    materialization: str,
    vars: dict[str, str],
    sources: dict[str, SourceInfo],
    ephemerals: dict[str, EphemeralModel] = ...,
) -> list[ResolvedModel]:
    """Batch resolve: parse and resolve all models in a single Rust call."""
    ...


def batch_wrap_ddl(models: list[ResolvedModel]) -> list[CompiledModel]:
    """Batch wrap DDL for all resolved models in a single Rust call."""
    ...


def select_models(
    dag: DagHandle,
    pattern: str,
    tags_map: dict[str, list[str]] = ...,
) -> list[str]:
    """Select models matching a dbt-style pattern."""
    ...
