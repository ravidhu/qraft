import sys
from pathlib import Path

import click
from rich.console import Console

from qraft import _core
from qraft.compiler.bridge import batch_compile, compile_model
from qraft.compiler.macro_expander import expand as expand_macros
from qraft.config.loader import load
from qraft.config.resolver import resolve_env
from qraft.dag.bridge import build_pipeline, scan_models
from qraft.engine import get_engine
from qraft.runner.runner import run, write_compiled

try:
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("qraft")
except Exception:
    __version__ = "dev"

console = Console()


@click.group()
@click.version_option(version=__version__, message="%(version)s")
def main():
    """Qraft — SQL templating and orchestration tool."""
    pass


@main.command()
@click.argument("project_name")
def init(project_name: str):
    """Create a new project. Use '.' to initialize in the current directory."""
    project_dir = Path(project_name).resolve()
    project_dir.mkdir(exist_ok=True)
    name = project_dir.name
    (project_dir / "models").mkdir(exist_ok=True)
    (project_dir / "macros").mkdir(exist_ok=True)

    (project_dir / "project.yaml").write_text(
        f"name: {name}\n\n"
        "connection:\n  type: duckdb\n  path: dev.duckdb\n\n"
        "schema: analytics\nmaterialization: view\n\n"
        "sources: {}\nvars: {}\n\n"
        "environments:\n  local:\n"
    )
    (project_dir / "models" / "example.sql").write_text(
        "-- Example model. Replace with your own!\n"
        "SELECT 1 AS id, 'hello' AS message\n"
    )
    (project_dir / ".env.example").write_text(
        "# Database connection\n"
        "# DB_HOST=localhost\n"
        "# DB_PORT=5432\n"
        "# DB_USER=your_db_user\n"
        "# DB_PASSWORD=your_db_password\n"
        "# DB_NAME=your_database\n"
    )
    (project_dir / ".gitignore").write_text(
        ".env\n*.duckdb\n*.duckdb.wal\n"
    )

    if project_name in (".", "./"):
        console.print(f"\n[green]Initialized project '{name}' in current directory[/green]")
        console.print("  Next: edit project.yaml\n")
    else:
        console.print(f"\n[green]Created {name}/[/green]")
        console.print(f"  Next: cd {name} && edit project.yaml\n")


@main.command(name="compile")
@click.option(
    "--env", "env_name", required=True, help="Target environment"
)
@click.option(
    "--select",
    "select_pattern",
    default=None,
    help="Model selection pattern",
)
@click.option(
    "--verbose", is_flag=True, help="Show compiled SQL with DDL"
)
def compile_cmd(
    env_name: str, select_pattern: str | None, verbose: bool
):
    """Resolve variables and refs — print compiled SQL."""
    from qraft.manifest import generate_manifest

    project = load(Path("."))
    env = resolve_env(project, env_name)
    models = scan_models(Path("models"))
    model_map = {model.name: model for model in models}

    # Build DAG pipeline: parse, build, validate, sort, select (single Rust call)
    available_sources = list(env.sources.keys())
    dag, batches, _parsed_models, errors = build_pipeline(
        models, available_sources, select=select_pattern
    )
    if errors:
        for error in errors:
            console.print(f"[red]{error.model}[/red]: {error.message}")
            if error.suggestion:
                console.print(f"  did you mean '{error.suggestion}'?")
        sys.exit(1)

    # Compile all models (batch: resolve all → macros → wrap DDL)
    all_models = [model_map[name] for batch in batches for name in batch]
    all_compiled = batch_compile(all_models, env, project_root=Path("."))
    compiled_map = {compiled_model.name: compiled_model for compiled_model in all_compiled}

    compiled_batches: list[list] = []
    for batch in batches:
        compiled_batch = []
        for name in batch:
            compiled = compiled_map[name]
            compiled_batch.append(compiled)
            if compiled.materialization == "ephemeral":
                continue
            console.print(
                f"\n[bold]── {compiled.name} "
                f"({env.connection.type}, env={env_name}) ──[/bold]\n"
            )
            if verbose:
                console.print(compiled.ddl)
            else:
                console.print(compiled.compiled_sql)
        compiled_batches.append(compiled_batch)

    output_dir = write_compiled(
        compiled_batches, model_map, env_name, Path("target")
    )
    generate_manifest(
        compiled_batches=compiled_batches,
        model_map=model_map,
        env=env,
        dag=dag,
        batches=batches,
        project_name=project.name,
        target_dir=Path("target"),
    )
    console.print(
        f"\n[dim]Compiled SQL written to {output_dir}/[/dim]"
    )


@main.command(name="run")
@click.option(
    "--env", "env_name", required=True, help="Target environment"
)
@click.option(
    "--select",
    "select_pattern",
    default=None,
    help="Model selection pattern",
)
@click.option(
    "--dry-run", is_flag=True, help="Preview without executing"
)
@click.option("--verbose", is_flag=True, help="Show detailed logs")
@click.option(
    "--parallel",
    default=4,
    help="Max parallel models per batch",
)
def run_cmd(
    env_name: str,
    select_pattern: str | None,
    dry_run: bool,
    verbose: bool,
    parallel: int,
):
    """Compile and execute models in DAG order."""
    project = load(Path("."))
    env = resolve_env(project, env_name)

    engine = get_engine(env.connection.type)
    engine.connect(env.connection)

    try:
        results = run(
            models_dir=Path("models"),
            env=env,
            engine=engine,
            select=select_pattern,
            parallel=parallel,
            dry_run=dry_run,
            target_dir=Path("target"),
            project_root=Path("."),
            project_name=project.name,
        )

        if not dry_run:
            _print_results(results)
            _exit_code(results)
    finally:
        engine.close()


@main.command()
def dag():
    """Show dependency graph."""
    models = scan_models(Path("models"))
    _dag, batches, parsed_models, _errors = build_pipeline(models, [])
    parsed_map = {parsed_model.name: parsed_model for parsed_model in parsed_models}

    for batch in batches:
        for name in batch:
            parsed_model = parsed_map[name]
            for ref in parsed_model.refs:
                console.print(f"  {ref:<30} → {name}")
            for source_name, table_name in parsed_model.sources:
                console.print(
                    f"  source({source_name}.{table_name}){'':>5} → {name}"
                )

    total = sum(len(b) for b in batches)
    console.print(f"\n{total} models, {len(batches)} layers.\n")


@main.command()
@click.option("--env", "env_name", required=True)
def validate(env_name: str):
    """Check refs, cycles, syntax, connections."""
    project = load(Path("."))
    env = resolve_env(project, env_name)
    models = scan_models(Path("models"))

    available_sources = list(env.sources.keys())
    _dag, _batches, _parsed_models, errors = build_pipeline(
        models, available_sources
    )

    if not errors:
        console.print("[green]All checks passed.[/green]")
    else:
        for error in errors:
            console.print(f"[red]✗ {error.model}[/red]  {error.message}")
            if error.suggestion:
                console.print(f"  → did you mean '{error.suggestion}'?")
        sys.exit(1)


@main.command()
@click.option("--env", "env_name", required=True)
@click.option("--yes", is_flag=True, help="Skip confirmation")
def clean(env_name: str, yes: bool):
    """Drop all managed objects in schema."""
    project = load(Path("."))
    env = resolve_env(project, env_name)
    models = scan_models(Path("models"))

    if not yes:
        console.print(
            f"\nThis will drop all objects in schema "
            f"[bold]{env.schema}[/bold]:"
        )
        for model in models:
            console.print(f"  - {model.name}")
        if not click.confirm("\nContinue?", default=False):
            return

    engine = get_engine(env.connection.type)
    engine.connect(env.connection)
    try:
        for model in models:
            target = f"{env.schema}.{model.name}"
            engine.drop(target, env.materialization)
        console.print(
            f"[green]Dropped {len(models)} objects.[/green]"
        )
    finally:
        engine.close()


@main.command(name="test-connection")
@click.option("--env", "env_name", required=True)
def test_connection(env_name: str):
    """Test connections for an environment."""
    project = load(Path("."))
    env = resolve_env(project, env_name)

    engine = get_engine(env.connection.type)
    engine.connect(env.connection)
    result = engine.test_connection()
    engine.close()

    if result.success:
        console.print(f"[green]✓ {result.details}[/green]")
    else:
        console.print(f"[red]✗ {result.details}[/red]")
        sys.exit(1)


@main.command()
@click.option("--env", "env_name", required=True)
@click.argument("model_name")
@click.option(
    "--expanded", is_flag=True, help="Show post-macro SQL"
)
def show(env_name: str, model_name: str, expanded: bool):
    """Show compiled SQL for a single model."""
    project = load(Path("."))
    env = resolve_env(project, env_name)
    models = scan_models(Path("models"))
    model = next((model for model in models if model.name == model_name), None)
    if model is None:
        console.print(f"[red]Model '{model_name}' not found.[/red]")
        sys.exit(1)

    if expanded:
        from qraft.compiler.bridge import _build_sources

        sources = _build_sources(env)
        resolved = _core.resolve_model(
            raw_sql=model.raw_sql,
            model_name=model.name,
            schema=env.schema,
            materialization=env.materialization,
            vars=env.vars,
            sources=sources,
        )
        sql = resolved.resolved_sql
        if resolved.macros:
            sql = expand_macros(
                sql=sql,
                macros_list=resolved.macros,
                vars=env.vars,
                model_name=resolved.name,
                project_root=Path("."),
            )
        console.print(
            f"\n[bold]-- {model_name} "
            f"(after macro expansion)[/bold]\n"
        )
        console.print(sql)
    else:
        compiled = compile_model(model, env, project_root=Path("."))
        console.print(compiled.compiled_sql)


@main.command(name="test")
@click.option(
    "--env", "env_name", required=True, help="Target environment"
)
@click.option(
    "--select",
    "select_pattern",
    default=None,
    help="Model selection pattern",
)
@click.option(
    "--fail-fast", is_flag=True, help="Stop on first test failure"
)
def test_cmd(
    env_name: str,
    select_pattern: str | None,
    fail_fast: bool,
):
    """Run data tests defined in model front-matter."""
    from qraft.testing.runner import run_tests

    project = load(Path("."))
    env = resolve_env(project, env_name)
    models = scan_models(Path("models"))

    engine = get_engine(env.connection.type)
    engine.connect(env.connection)

    try:
        results = run_tests(
            models=models,
            engine=engine,
            schema=env.schema,
            select=select_pattern,
            fail_fast=fail_fast,
        )

        if not results:
            console.print("[dim]No tests found.[/dim]")
            return

        _print_test_results(results)
        _write_test_results(results, env_name, env.schema)
        _exit_code_tests(results)
    finally:
        engine.close()


@main.command(name="build")
@click.option(
    "--env", "env_name", required=True, help="Target environment"
)
@click.option(
    "--select",
    "select_pattern",
    default=None,
    help="Model selection pattern",
)
@click.option("--verbose", is_flag=True, help="Show detailed logs")
@click.option(
    "--parallel",
    default=4,
    help="Max parallel models per batch",
)
@click.option(
    "--fail-fast", is_flag=True, help="Stop on first test failure"
)
def build_cmd(
    env_name: str,
    select_pattern: str | None,
    verbose: bool,
    parallel: int,
    fail_fast: bool,
):
    """Run models then tests in DAG order."""
    from qraft.testing.runner import run_tests

    project = load(Path("."))
    env = resolve_env(project, env_name)

    engine = get_engine(env.connection.type)
    engine.connect(env.connection)

    try:
        # Phase 1: Run models
        results = run(
            models_dir=Path("models"),
            env=env,
            engine=engine,
            select=select_pattern,
            parallel=parallel,
            target_dir=Path("target"),
            project_root=Path("."),
            project_name=project.name,
        )

        _print_results(results)

        # Check for model failures before running tests
        has_model_failures = any(
            m.status == "failed"
            for batch in results
            for m in batch.models
        )
        if has_model_failures:
            console.print(
                "\n[red]Skipping tests due to model failures.[/red]"
            )
            sys.exit(1)

        # Phase 2: Run tests
        # Re-connect since run() closes the connection
        engine.connect(env.connection)
        models = scan_models(Path("models"))
        test_results = run_tests(
            models=models,
            engine=engine,
            schema=env.schema,
            select=select_pattern,
            fail_fast=fail_fast,
        )

        if test_results:
            console.print("\n[bold]── Tests ──[/bold]\n")
            _print_test_results(test_results)
            _write_test_results(test_results, env_name, env.schema)
            _exit_code_tests(test_results)
        else:
            console.print("\n[dim]No tests found.[/dim]")
    finally:
        engine.close()


def _print_test_results(results: list) -> None:
    """Print test execution results."""
    passed = 0
    failed = 0
    warned = 0
    errored = 0

    for test_result in results:
        test = test_result.test
        label = f"{test.model_name}.{test.column} ({test.test_type})"

        if test_result.error:
            errored += 1
            console.print(f"  [red]ERROR[/red] {label}: {test_result.error}")
        elif test_result.passed:
            passed += 1
            console.print(f"  [green]PASS[/green]  {label}")
        elif test.severity == "warn":
            warned += 1
            console.print(
                f"  [yellow]WARN[/yellow]  {label} "
                f"({test_result.failures_count} failures)"
            )
        else:
            failed += 1
            console.print(
                f"  [red]FAIL[/red]  {label} "
                f"({test_result.failures_count} failures)"
            )
            if test_result.failures_sample:
                for row in test_result.failures_sample[:3]:
                    console.print(f"         {row}")

    total = passed + failed + warned + errored
    parts = [f"{total} tests"]
    if passed:
        parts.append(f"{passed} passed")
    if failed:
        parts.append(f"{failed} failed")
    if warned:
        parts.append(f"{warned} warnings")
    if errored:
        parts.append(f"{errored} errors")

    color = "green" if failed == 0 and errored == 0 else "red"
    console.print(f"\n[{color}]{', '.join(parts)}.[/{color}]")


def _write_test_results(results: list, env_name: str, schema: str) -> None:
    """Write test results to target/test_results.json."""
    from qraft.testing.results import write_test_results

    out_path = write_test_results(results, env_name, schema, Path("target"))
    console.print(f"\n[dim]Test results written to {out_path}[/dim]")


def _exit_code_tests(results: list) -> None:
    """Exit with code 1 if any error-severity tests failed."""
    for test_result in results:
        if not test_result.passed and test_result.test.severity == "error":
            sys.exit(1)


def _print_results(results: list) -> None:
    """Print execution results."""
    total = 0
    ok = 0
    failed = 0
    skipped = 0
    for batch in results:
        for model in batch.models:
            total += 1
            if model.status == "success":
                ok += 1
                console.print(
                    f"  [green]✓[/green] {model.name:<25} "
                    f"{model.duration_ms}ms"
                )
            elif model.status == "failed":
                failed += 1
                console.print(
                    f"  [red]✗[/red] {model.name:<25} "
                    f"{model.error}"
                )
            else:
                skipped += 1
                console.print(
                    f"  [yellow]⊘[/yellow] {model.name:<25} SKIPPED"
                )

    if failed == 0:
        console.print(f"\n[green]Done. {total} models.[/green]")
    else:
        console.print(
            f"\n[red]Failed. {ok} ok, {failed} failed, "
            f"{skipped} skipped.[/red]"
        )


def _exit_code(results: list) -> None:
    for batch in results:
        for model in batch.models:
            if model.status == "failed":
                sys.exit(1)


# ── Docs ───────────────────────────────────────────────────────


@main.group()
def docs():
    """Generate and serve project documentation catalog."""
    pass


@docs.command(name="generate")
@click.option(
    "--env", "env_name", required=True, help="Target environment"
)
@click.option(
    "--select",
    "select_pattern",
    default=None,
    help="Model selection pattern",
)
@click.option(
    "--target-dir",
    default="target",
    type=click.Path(),
    help="Target directory",
)
def docs_generate(
    env_name: str, select_pattern: str | None, target_dir: str
):
    """Generate catalog site from compiled manifest."""
    from qraft.catalog.generator import generate_catalog
    from qraft.manifest import generate_manifest

    target = Path(target_dir)
    manifest_path = target / "manifest.json"

    # If manifest doesn't exist, compile first
    if not manifest_path.exists():
        console.print("[dim]No manifest found, compiling...[/dim]")
        project = load(Path("."))
        env = resolve_env(project, env_name)
        models = scan_models(Path("models"))
        model_map = {model.name: model for model in models}

        available_sources = list(env.sources.keys())
        dag, batches, _parsed, errors = build_pipeline(
            models, available_sources, select=select_pattern
        )
        if errors:
            for error in errors:
                console.print(f"[red]{error.model}[/red]: {error.message}")
            sys.exit(1)

        all_models = [
            model_map[name] for batch in batches for name in batch
        ]
        all_compiled = batch_compile(
            all_models, env, project_root=Path(".")
        )
        compiled_map = {compiled_model.name: compiled_model for compiled_model in all_compiled}
        compiled_batches = [
            [compiled_map[name] for name in batch] for batch in batches
        ]

        generate_manifest(
            compiled_batches=compiled_batches,
            model_map=model_map,
            env=env,
            dag=dag,
            batches=batches,
            project_name=project.name,
            target_dir=target,
        )

    catalog_dir = generate_catalog(target)
    console.print(
        f"[green]Catalog generated at {catalog_dir}/[/green]"
    )
    console.print(
        "[dim]Run 'qraft docs serve' to view it.[/dim]"
    )


@docs.command(name="serve")
@click.option(
    "--port", default=8080, type=int, help="Port to serve on"
)
@click.option(
    "--target-dir",
    default="target",
    type=click.Path(),
    help="Target directory",
)
def docs_serve(port: int, target_dir: str):
    """Start local server to view generated catalog."""
    from qraft.catalog.server import serve_catalog

    catalog_dir = Path(target_dir) / "catalog"
    if not (catalog_dir / "index.html").exists():
        console.print(
            "[red]Catalog not found.[/red] "
            "Run 'qraft docs generate --env <env>' first."
        )
        sys.exit(1)

    serve_catalog(catalog_dir, port)
