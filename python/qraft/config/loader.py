from pathlib import Path

import yaml

from qraft.config.models import ConnectionConfig, ProjectConfig, SourceConfig
from qraft.utils.env import resolve_env_vars

_VALID_MATERIALIZATIONS = {
    "view", "table", "ephemeral", "table_incremental", "materialized_view",
}


class ConfigValidationError(Exception):
    """Raised when project.yaml contains invalid or missing configuration."""


def _validate_raw_config(raw: dict, config_path: Path) -> None:
    """Validate the raw YAML configuration before constructing objects."""
    errors: list[str] = []

    # Required top-level fields
    if "name" not in raw or not raw["name"]:
        errors.append("'name' is required")

    if "connection" not in raw or not isinstance(raw.get("connection"), dict):
        errors.append("'connection' is required and must be a mapping")
    else:
        conn = raw["connection"]
        if "type" not in conn:
            errors.append("'connection.type' is required")

    # Materialization
    materialization = raw.get("materialization", "view")
    if materialization not in _VALID_MATERIALIZATIONS:
        errors.append(
            f"'materialization' must be one of {sorted(_VALID_MATERIALIZATIONS)}, "
            f"got '{materialization}'"
        )

    # Sources validation
    sources = raw.get("sources", {})
    if sources and not isinstance(sources, dict):
        errors.append("'sources' must be a mapping")
    elif isinstance(sources, dict):
        for name, source_config in sources.items():
            if not isinstance(source_config, dict):
                errors.append(f"source '{name}' must be a mapping")
                continue
            if "schema" not in source_config and "tables" not in source_config:
                errors.append(
                    f"source '{name}' must have at least 'schema' or 'tables'"
                )
            tables = source_config.get("tables", [])
            if tables and not isinstance(tables, list):
                errors.append(f"source '{name}.tables' must be a list")

    # Vars validation
    current_variables = raw.get("vars", {})
    if current_variables and not isinstance(current_variables, dict):
        errors.append("'vars' must be a mapping")

    # Environments validation
    envs = raw.get("environments", {})
    if envs and not isinstance(envs, dict):
        errors.append("'environments' must be a mapping")
    elif isinstance(envs, dict):
        for env_name, env_config in envs.items():
            if env_config is None:
                continue  # Empty environment = inherit defaults
            if not isinstance(env_config, dict):
                errors.append(f"environment '{env_name}' must be a mapping")
                continue
            materialization = env_config.get("materialization")
            if materialization is not None and materialization not in _VALID_MATERIALIZATIONS:
                errors.append(
                    f"environment '{env_name}'.materialization must be one of "
                    f"{sorted(_VALID_MATERIALIZATIONS)}, got '{materialization}'"
                )
            connection = env_config.get("connection")
            if connection is not None:
                if not isinstance(connection, dict):
                    errors.append(
                        f"environment '{env_name}'.connection must be a mapping"
                    )

    if errors:
        error_list = "\n  - ".join(errors)
        raise ConfigValidationError(
            f"Invalid configuration in {config_path}:\n  - {error_list}"
        )


def load(project_dir: Path) -> ProjectConfig:
    """Parse and validate project.yaml → ProjectConfig.

    Reads the YAML file, resolves ``${ENV_VAR}`` placeholders, validates the
    structure and values, and returns a typed ``ProjectConfig``.

    Raises:
        FileNotFoundError: If ``project.yaml`` is not found in *project_dir*.
        ConfigValidationError: If the configuration contains invalid or missing fields.
    """
    config_path = project_dir / "project.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"project.yaml not found in {project_dir}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    # Resolve ${ENV_VAR} in the raw YAML
    raw = resolve_env_vars(raw)

    # Validate before constructing objects
    _validate_raw_config(raw, config_path)

    connection = ConnectionConfig(
        type=raw["connection"]["type"],
        params={
            k: v for k, v in raw["connection"].items() if k != "type"
        },
    )

    sources = {}
    for name, source_config in raw.get("sources", {}).items():
        sources[name] = SourceConfig(
            name=name,
            database=source_config.get("database"),
            schema=source_config.get("schema", ""),
            tables=source_config.get("tables", []),
            connection=_parse_source_connection(source_config),
        )

    return ProjectConfig(
        name=raw["name"],
        version=raw.get("version", "0.0.0"),
        connection=connection,
        schema=raw.get("schema", "public"),
        materialization=raw.get("materialization", "view"),
        sources=sources,
        vars=raw.get("vars", {}),
        environments=raw.get("environments", {}),
    )


def _parse_source_connection(source_config: dict) -> ConnectionConfig | None:
    if "type" in source_config and "tables" in source_config:
        return ConnectionConfig(
            type=source_config["type"],
            params={
                k: v
                for k, v in source_config.items()
                if k not in ("type", "tables", "database", "schema", "name")
            },
        )
    return None
