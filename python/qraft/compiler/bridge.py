from pathlib import Path

from qraft import _core
from qraft.compiler.macro_expander import expand as expand_macros
from qraft.config.models import EnvConfig, Model

_ENGINE_SUPPORTED_MATERIALIZATIONS: dict[str, set[str]] = {
    "duckdb": {"view", "table", "ephemeral", "table_incremental"},
    "postgres": {"view", "table", "ephemeral", "table_incremental", "materialized_view"},
    "mysql": {"view", "table", "ephemeral", "table_incremental"},
    "trino": {"view", "table", "ephemeral", "table_incremental", "materialized_view"},
}


def _validate_engine_materialization(
    engine_type: str, materialization: str, model_name: str
) -> None:
    supported = _ENGINE_SUPPORTED_MATERIALIZATIONS.get(engine_type)
    if supported is not None and materialization not in supported:
        raise ValueError(
            f"Materialization '{materialization}' is not supported by engine "
            f"'{engine_type}' in model '{model_name}'. "
            f"Supported: {', '.join(sorted(supported))}."
        )


def compile_model(
    model: Model,
    env: EnvConfig,
    project_root: Path | None = None,
) -> _core.CompiledModel:
    """Compile a single model through the full pipeline.

    Performs three phases:
    1. **Resolve** — replace ``ref()``, ``source()``, ``{{ var }}`` via Rust
    2. **Expand macros** — call Python macro functions if the model declares any
    3. **Wrap DDL** — generate the final executable statement (CREATE VIEW, etc.)

    Args:
        model: The scanned SQL model to compile.
        env: Resolved environment configuration.
        project_root: Project root for locating ``macros/`` directory.

    Returns:
        A compiled model with resolved SQL and DDL ready for execution.

    Raises:
        ValueError: If the model's materialization is unsupported by the engine.
    """
    sources = _build_sources(env)

    resolved = _core.resolve_model(
        raw_sql=model.raw_sql,
        model_name=model.name,
        schema=env.schema,
        materialization=env.materialization,
        vars=env.vars,
        sources=sources,
    )

    _validate_engine_materialization(
        env.connection.type, resolved.materialization, model.name
    )

    sql = resolved.resolved_sql

    if resolved.macros and project_root is not None:
        macro_vars = {**env.vars, "engine": env.connection.type}
        sql = expand_macros(
            sql=sql,
            macros_list=resolved.macros,
            vars=macro_vars,
            model_name=resolved.name,
            project_root=project_root,
        )

    if sql != resolved.resolved_sql:
        return _core.wrap_ddl(resolved, resolved_sql=sql)

    return _core.wrap_ddl(resolved)


def _build_ephemerals(
    models: list[Model],
    env: EnvConfig,
    sources: dict[str, _core.SourceInfo],
) -> dict[str, _core.EphemeralModel]:
    """Identify ephemeral models and pre-resolve them for CTE injection.

    Ephemeral models are not materialized as database objects. Instead, their
    compiled SQL is injected as CTEs into downstream models that reference them.
    This function scans all models for ``materialization: ephemeral`` in
    front-matter and resolves them so the main batch_resolve can inject their
    SQL as CTEs.

    Args:
        models: All scanned models (ephemeral and non-ephemeral).
        env: Resolved environment configuration.
        sources: Source info map for resolving ``source()`` calls.

    Returns:
        Mapping of model name → EphemeralModel for all ephemeral models.
    """
    # Pre-parse to find ephemeral models
    ephemeral_models: list[Model] = []
    for model in models:
        parsed = _core.parse_sql(model.raw_sql)
        front_matter = parsed.front_matter
        materialization = front_matter.get("materialization", "") if front_matter else ""
        if materialization == "ephemeral":
            ephemeral_models.append(model)

    if not ephemeral_models:
        return {}

    # Resolve ephemeral models (they may depend on each other, handled transitively)
    raw_ephemeral_models = [(model.name, model.raw_sql) for model in ephemeral_models]
    resolved_ephemeral_models = _core.batch_resolve(
        raw_models=raw_ephemeral_models,
        schema=env.schema,
        materialization=env.materialization,
        vars=env.vars,
        sources=sources,
    )

    ephemerals: dict[str, _core.EphemeralModel] = {}
    for resolved in resolved_ephemeral_models:
        ephemerals[resolved.name] = _core.EphemeralModel(
            name=resolved.name,
            compiled_body=resolved.resolved_sql,
            deps=resolved.refs,
        )
    return ephemerals


def batch_compile(
    models: list[Model],
    env: EnvConfig,
    project_root: Path | None = None,
) -> list[_core.CompiledModel]:
    """Compile multiple models in an optimized batch pipeline.

    This is the primary compilation entry point used by ``qraft run`` and
    ``qraft compile``. It minimizes Python↔Rust boundary crossings:

    1. ``batch_resolve()`` — single Rust call to parse and resolve all models
    2. ``expand_macros()`` — Python-side macro expansion for models that need it
    3. ``batch_wrap_ddl()`` — single Rust call to wrap DDL for non-macro models,
       plus individual ``wrap_ddl()`` calls for macro-expanded models

    This gives 2–3 Rust calls total instead of 2N for N models.

    Args:
        models: List of scanned SQL models to compile.
        env: Resolved environment configuration.
        project_root: Project root for locating ``macros/`` directory.

    Returns:
        List of compiled models in the same order as the input.

    Raises:
        ValueError: If any model's materialization is unsupported by the engine.
    """
    sources = _build_sources(env)
    raw_models = [(model.name, model.raw_sql) for model in models]

    # Phase 0: build ephemerals map from ephemeral models
    ephemerals = _build_ephemerals(models, env, sources)

    # Phase 1: batch resolve all models (single Rust call)
    resolved_list = _core.batch_resolve(
        raw_models=raw_models,
        schema=env.schema,
        materialization=env.materialization,
        vars=env.vars,
        sources=sources,
        ephemerals=ephemerals,
    )

    # Phase 2: expand macros in Python + validate materializations
    # Track which models had macro expansion (need individual wrap_ddl)
    macro_expanded: dict[int, str] = {}
    for i, resolved in enumerate(resolved_list):
        _validate_engine_materialization(
            env.connection.type, resolved.materialization, resolved.name
        )
        if resolved.macros and project_root is not None:
            macro_vars = {**env.vars, "engine": env.connection.type}
            expanded = expand_macros(
                sql=resolved.resolved_sql,
                macros_list=resolved.macros,
                vars=macro_vars,
                model_name=resolved.name,
                project_root=project_root,
            )
            if expanded != resolved.resolved_sql:
                macro_expanded[i] = expanded

    # Phase 3: wrap DDL
    # Non-macro models: batch wrap (single Rust call)
    # Macro models: individual wrap_ddl with overridden SQL
    compiled_results: list[_core.CompiledModel | None] = [None] * len(resolved_list)

    non_macro_indices = [i for i in range(len(resolved_list)) if i not in macro_expanded]
    if non_macro_indices:
        non_macro_resolved = [resolved_list[i] for i in non_macro_indices]
        batch_compiled = _core.batch_wrap_ddl(non_macro_resolved)
        for idx, compiled in zip(non_macro_indices, batch_compiled):
            compiled_results[idx] = compiled

    for i, expanded_sql in macro_expanded.items():
        compiled_results[i] = _core.wrap_ddl(resolved_list[i], resolved_sql=expanded_sql)

    return compiled_results


def _build_sources(env: EnvConfig) -> dict[str, _core.SourceInfo]:
    """Convert Python source configs to Rust SourceInfo objects.

    Args:
        env: Resolved environment configuration containing source definitions.

    Returns:
        Mapping of source name → SourceInfo (database + schema) for Rust.
    """
    sources = {}
    for name, source_config in env.sources.items():
        sources[name] = _core.SourceInfo(
            database=source_config.database or "",
            schema=source_config.schema,
        )
    return sources


def parse_sql(raw_sql: str) -> _core.ParsedSQL:
    """Parse a SQL file via Rust: extract refs, sources, variables."""
    return _core.parse_sql(raw_sql)
