import shutil
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from qraft import _core
from qraft.compiler.bridge import batch_compile
from qraft.config.models import ConnectionConfig, EnvConfig, Model
from qraft.dag.bridge import build_pipeline, scan_models
from qraft.engine.base import Engine


# ─────────────────────────────────
# Result types (replace Rust ModelResult / BatchResult)
# ─────────────────────────────────


@dataclass(frozen=True)
class ModelResult:
    name: str
    status: str  # "success", "failed", "skipped"
    duration_ms: int
    error: str | None


@dataclass(frozen=True)
class BatchResult:
    batch_index: int
    models: list[ModelResult]


# ─────────────────────────────────
# Picklable task sent to worker processes
# ─────────────────────────────────


@dataclass
class ModelTask:
    name: str
    ddl: str
    compiled_sql: str
    target: str
    materialization: str


# ─────────────────────────────────
# Worker process functions (module-level for pickling)
# ─────────────────────────────────

_worker_engine: Engine | None = None


def _init_worker(engine_type: str, connection_params: dict) -> None:
    """Called once per worker process to create a DB connection."""
    global _worker_engine
    from qraft.engine import get_engine

    _worker_engine = get_engine(engine_type)
    _worker_engine.connect(
        ConnectionConfig(type=engine_type, params=connection_params)
    )


def _execute_task(task: ModelTask) -> ModelResult:
    """Execute a single model in a worker process."""
    global _worker_engine
    start = time.perf_counter()
    try:
        if task.materialization == "table_incremental":
            if not _worker_engine.object_exists(task.target):
                _worker_engine.execute(
                    f"CREATE TABLE {task.target} AS\n{task.compiled_sql}"
                )
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                return ModelResult(
                    name=task.name,
                    status="success",
                    duration_ms=elapsed_ms,
                    error=None,
                )
        _worker_engine.execute(task.ddl)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ModelResult(
            name=task.name,
            status="success",
            duration_ms=elapsed_ms,
            error=None,
        )
    except Exception as error:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ModelResult(
            name=task.name,
            status="failed",
            duration_ms=elapsed_ms,
            error=str(error),
        )


# ─────────────────────────────────
# Batch execution
# ─────────────────────────────────


def _run_batches(
    compiled_batches: list[list[_core.CompiledModel]],
    engine_type: str,
    connection_params: dict,
    parallel: int,
) -> list[BatchResult]:
    """Execute compiled model batches using multiprocessing."""
    failed_models: set[str] = set()
    all_results: list[BatchResult] = []

    with ProcessPoolExecutor(
        max_workers=parallel,
        initializer=_init_worker,
        initargs=(engine_type, connection_params),
    ) as pool:
        for batch_idx, batch in enumerate(compiled_batches):
            tasks: list[ModelTask] = []
            skipped: list[ModelResult] = []

            for compiled in batch:
                # Ephemeral models are inlined as CTEs — nothing to execute
                if compiled.materialization == "ephemeral":
                    continue
                if any(ref in failed_models for ref in compiled.refs):
                    skipped.append(
                        ModelResult(
                            name=compiled.name,
                            status="skipped",
                            duration_ms=0,
                            error="Skipped: depends on failed model",
                        )
                    )
                else:
                    tasks.append(
                        ModelTask(
                            name=compiled.name,
                            ddl=compiled.ddl,
                            compiled_sql=compiled.compiled_sql,
                            target=compiled.target,
                            materialization=compiled.materialization,
                        )
                    )

            results = list(pool.map(_execute_task, tasks))
            results.extend(skipped)

            for model_result in results:
                if model_result.status == "failed":
                    failed_models.add(model_result.name)

            all_results.append(
                BatchResult(batch_index=batch_idx, models=results)
            )

    return all_results


# ─────────────────────────────────
# Public API
# ─────────────────────────────────


def run(
    models_dir: Path,
    env: EnvConfig,
    engine: Engine,
    select: str | None = None,
    parallel: int = 4,
    dry_run: bool = False,
    target_dir: Path | None = None,
    project_root: Path | None = None,
    project_name: str = "",
) -> list[BatchResult]:
    """Full pipeline: scan → DAG → compile → write → execute."""

    # 1. Scan models
    models = scan_models(models_dir)
    model_map = {model.name: model for model in models}

    # 2. Build DAG pipeline: parse → build → validate → sort → select (single Rust call)
    available_sources = list(env.sources.keys())
    dag, batches, _parsed_models, errors = build_pipeline(
        models, available_sources, select=select
    )
    if errors:
        from rich.console import Console

        console = Console()
        for error in errors:
            console.print(f"[red]{error.model}[/red]: {error.message}")
            if error.suggestion:
                console.print(f"  did you mean '{error.suggestion}'?")
        raise SystemExit(1)

    # 5. Compile models (batch: resolve all → macros → wrap DDL)
    all_models = [model_map[name] for batch in batches for name in batch]
    all_compiled = batch_compile(all_models, env, project_root=project_root)
    compiled_map = {compiled_model.name: compiled_model for compiled_model in all_compiled}

    compiled_batches: list[list[_core.CompiledModel]] = [
        [compiled_map[name] for name in batch] for batch in batches
    ]

    # 6. Write compiled SQL to target/
    if target_dir is not None:
        write_compiled(
            compiled_batches, model_map, env.name, target_dir
        )

    # 6.5. Generate manifest
    if target_dir is not None:
        from qraft.manifest import generate_manifest

        generate_manifest(
            compiled_batches=compiled_batches,
            model_map=model_map,
            env=env,
            dag=dag,
            batches=batches,
            project_name=project_name,
            target_dir=target_dir,
        )

    # 7. Dry run: print without executing
    if dry_run:
        _print_dry_run(compiled_batches)
        return []

    # 8. Create all needed schemas (main env schema + per-model overrides)
    schemas = {env.schema}
    for batch in compiled_batches:
        for compiled in batch:
            if compiled.materialization != "ephemeral":
                schema = compiled.target.rsplit(".", 1)[0]
                schemas.add(schema)
    for schema in schemas:
        engine.create_schema(schema)

    # 9. DuckDB only allows one write connection at a time (exclusive file lock),
    #    so cap parallelism to 1 to avoid noisy lock errors.
    if env.connection.type == "duckdb":
        parallel = 1

    # 10. Release main connection so worker processes can access the DB
    engine.close()

    # 11. Execute via multiprocessing
    results = _run_batches(
        compiled_batches=compiled_batches,
        engine_type=env.connection.type,
        connection_params=env.connection.params,
        parallel=parallel,
    )

    return results


def write_compiled(
    compiled_batches: list[list[_core.CompiledModel]],
    model_map: dict[str, Model],
    env_name: str,
    target_dir: Path,
) -> Path:
    """Write compiled DDL to target/compiled/<env>/, mirroring models/ structure."""
    output_dir = target_dir / "compiled" / env_name
    if output_dir.exists():
        shutil.rmtree(output_dir)
    for batch in compiled_batches:
        for compiled in batch:
            model = model_map.get(compiled.name)
            if model is not None:
                out_path = output_dir / model.path
            else:
                out_path = output_dir / f"{compiled.name}.sql"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(compiled.ddl + "\n", encoding="utf-8")
    return output_dir


def _print_dry_run(
    batches: list[list[_core.CompiledModel]],
) -> None:
    from rich.console import Console

    console = Console()
    console.print("\n[bold]Would execute (in order):[/bold]\n")
    idx = 1
    for batch in batches:
        for model in batch:
            materialization = (
                "VIEW" if model.materialization == "view" else "TABLE"
            )
            console.print(
                f"  {idx}. {model.name:<25} → CREATE {materialization} {model.target}"
            )
            idx += 1
