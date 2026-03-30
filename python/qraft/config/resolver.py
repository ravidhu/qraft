from copy import deepcopy

from qraft.config.models import (
    ConnectionConfig,
    EnvConfig,
    ProjectConfig,
    SourceConfig,
)


def resolve_env(project: ProjectConfig, env_name: str) -> EnvConfig:
    """Deep merge environment overrides with defaults → EnvConfig."""
    if env_name not in project.environments:
        available = ", ".join(project.environments.keys())
        raise ValueError(
            f'Environment "{env_name}" not found in project.yaml.\n'
            f"Available environments: {available}"
        )

    overrides = project.environments[env_name] or {}

    # Connection: deep merge or swap if type changes
    connection = _merge_connection(
        project.connection, overrides.get("connection")
    )

    # Schema and materialization
    schema = overrides.get("schema", project.schema)
    materialization = overrides.get(
        "materialization", project.materialization
    )

    # Sources: deep merge per source
    sources = deepcopy(project.sources)
    for name, src_override in overrides.get("sources", {}).items():
        if name in sources:
            sources[name] = _merge_source(sources[name], src_override)

    # Vars: simple merge
    current_variables = {**project.vars, **overrides.get("vars", {})}

    return EnvConfig(
        name=env_name,
        connection=connection,
        schema=schema,
        materialization=materialization,
        sources=sources,
        vars=current_variables,
    )


def _merge_connection(
    default: ConnectionConfig,
    override: dict | None,
) -> ConnectionConfig:
    if override is None:
        return deepcopy(default)
    override_type = override.get("type", default.type)
    if override_type != default.type:
        # Type change → take only the override
        return ConnectionConfig(
            type=override_type,
            params={k: v for k, v in override.items() if k != "type"},
        )
    # Same type → deep merge params
    merged_params = {
        **default.params,
        **{k: v for k, v in override.items() if k != "type"},
    }
    return ConnectionConfig(type=default.type, params=merged_params)


def _merge_source(
    default: SourceConfig, override: dict
) -> SourceConfig:
    return SourceConfig(
        name=default.name,
        database=override.get("database", default.database),
        schema=override.get("schema", default.schema),
        tables=override.get("tables", default.tables),
        connection=default.connection,
    )
