"""Qraft — Lightweight SQL templating and orchestration tool."""

__version__ = "0.1.0"

# Public API — import these for programmatic usage
from qraft.config.loader import load as load_config
from qraft.config.resolver import resolve_env
from qraft.config.models import (
    ConnectionConfig,
    EnvConfig,
    Model,
    ProjectConfig,
    SourceConfig,
)
from qraft.dag.bridge import build_pipeline, scan_models
from qraft.compiler.bridge import batch_compile, compile_model, parse_sql
from qraft.runner.runner import run, write_compiled, BatchResult, ModelResult
from qraft.engine import get_engine
from qraft.engine.base import Engine, ConnectionTestResult

__all__ = [
    # Version
    "__version__",
    # Config
    "load_config",
    "resolve_env",
    "ConnectionConfig",
    "EnvConfig",
    "Model",
    "ProjectConfig",
    "SourceConfig",
    # DAG
    "build_pipeline",
    "scan_models",
    # Compilation
    "batch_compile",
    "compile_model",
    "parse_sql",
    # Execution
    "run",
    "write_compiled",
    "BatchResult",
    "ModelResult",
    # Engine
    "get_engine",
    "Engine",
    "ConnectionTestResult",
]
