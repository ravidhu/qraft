from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConnectionConfig:
    type: str  # duckdb, trino, postgres, ...
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class SourceConfig:
    name: str
    schema: str
    tables: list[str]
    database: str | None = None
    connection: ConnectionConfig | None = None


@dataclass
class EnvConfig:
    """Resolved config for a given environment (after deep merge)."""

    name: str
    connection: ConnectionConfig
    schema: str
    materialization: str
    sources: dict[str, SourceConfig]
    vars: dict[str, str]


@dataclass
class ProjectConfig:
    """Raw config parsed from project.yaml."""

    name: str
    version: str
    connection: ConnectionConfig
    schema: str
    materialization: str
    sources: dict[str, SourceConfig]
    vars: dict[str, str]
    environments: dict[str, dict]  # raw overrides, not yet resolved


@dataclass
class Model:
    """A SQL file scanned from models/."""

    name: str  # filename without extension
    path: Path  # relative path from models/
    raw_sql: str  # raw content
