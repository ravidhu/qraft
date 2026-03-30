"""Benchmark Qraft's Rust-powered compilation pipeline.

Measures parse → DAG → compile times across example projects
and synthetic model sets to showcase Rust core performance.
"""

import statistics
import sys
import tempfile
import textwrap
import time
from pathlib import Path

from qraft import _core
from qraft.compiler.bridge import batch_compile
from qraft.config.loader import load as load_project
from qraft.config.models import ConnectionConfig, EnvConfig, Model, SourceConfig
from qraft.config.resolver import resolve_env
from qraft.dag.bridge import build_pipeline, scan_models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_env(engine: str = "duckdb") -> EnvConfig:
    """Create a minimal EnvConfig for benchmarking (no real DB needed)."""
    return EnvConfig(
        name="bench",
        connection=ConnectionConfig(type=engine),
        schema="bench",
        materialization="view",
        vars={"trial_days": "14", "churn_inactive_days": "30"},
        sources={
            "raw": SourceConfig(name="raw", database="db", schema="raw_data", tables=["t"]),
            "crm": SourceConfig(name="crm", database="source_pg", schema="crm_raw", tables=["accounts"]),
            "billing": SourceConfig(name="billing", database="source_pg", schema="billing_raw", tables=["subscriptions"]),
            "product": SourceConfig(name="product", database="source_pg", schema="product_raw", tables=["users"]),
        },
    )


def _generate_synthetic_models(n: int, dest: Path) -> None:
    """Generate n synthetic SQL models with a linear DAG (each refs the previous)."""
    dest.mkdir(parents=True, exist_ok=True)

    # First model: sources from raw
    (dest / "model_000.sql").write_text(textwrap.dedent("""\
        ---
        description: Base model
        tags: [staging]
        ---
        SELECT id, name, created_at
        FROM source('raw', 't')
        WHERE created_at > '2024-01-01'
    """))

    for i in range(1, n):
        prev = f"model_{i - 1:03d}"
        sql = textwrap.dedent(f"""\
            ---
            description: Derived model {i}
            tags: [derived]
            ---
            SELECT
                id,
                name,
                created_at,
                COUNT(*) OVER (PARTITION BY name) AS name_count
            FROM ref('{prev}')
            WHERE created_at IS NOT NULL
        """)
        (dest / f"model_{i:03d}.sql").write_text(sql)


def _timeit(fn, *, warmup: int = 2, runs: int = 10) -> dict:
    """Run fn() multiple times and return timing stats in milliseconds."""
    for _ in range(warmup):
        fn()

    times = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)

    return {
        "median_ms": round(statistics.median(times), 3),
        "mean_ms": round(statistics.mean(times), 3),
        "min_ms": round(min(times), 3),
        "max_ms": round(max(times), 3),
        "stdev_ms": round(statistics.stdev(times), 3) if len(times) > 1 else 0,
        "runs": runs,
    }


# ---------------------------------------------------------------------------
# Benchmark functions
# ---------------------------------------------------------------------------

def bench_parse(models: list[Model]) -> dict:
    """Benchmark: parse all SQL files (extract refs, sources, front-matter)."""
    def run():
        for m in models:
            _core.parse_sql(m.raw_sql)
    return _timeit(run)


def bench_dag_pipeline(models: list[Model], sources: list[str]) -> dict:
    """Benchmark: full DAG pipeline (parse → build → validate → sort)."""
    def run():
        _core.build_pipeline(
            [(m.name, m.raw_sql) for m in models],
            sources,
        )
    return _timeit(run)


def bench_batch_compile(models: list[Model], env: EnvConfig) -> dict:
    """Benchmark: full compilation (resolve + DDL wrapping)."""
    def run():
        batch_compile(models, env, project_root=None)
    return _timeit(run)


def bench_end_to_end(models: list[Model], env: EnvConfig, sources: list[str]) -> dict:
    """Benchmark: DAG pipeline + batch compile (full pipeline)."""
    def run():
        dag, batches, _parsed, _errors = build_pipeline(models, sources)
        all_models = [m for m in models if m.name in {n for b in batches for n in b}]
        batch_compile(all_models, env, project_root=None)
    return _timeit(run)


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------

def run_example_benchmarks() -> list[dict]:
    """Benchmark each example project."""
    examples_dir = Path(__file__).parent.parent / "examples"
    results = []

    for project_dir in sorted(examples_dir.iterdir()):
        models_dir = project_dir / "models"
        project_yaml = project_dir / "project.yaml"
        if not models_dir.exists() or not project_yaml.exists():
            continue

        models = scan_models(models_dir)
        if not models:
            continue

        # Load actual project config to get correct vars/sources
        project = load_project(project_dir)
        # Pick first available environment
        env_name = next(iter(project.environments), None)
        if env_name is None:
            continue
        env = resolve_env(project, env_name)
        sources = list(env.sources.keys())

        name = project_dir.name
        n = len(models)

        parse = bench_parse(models)
        dag = bench_dag_pipeline(models, sources)
        compile_ = bench_batch_compile(models, env)
        e2e = bench_end_to_end(models, env, sources)

        results.append({
            "project": name,
            "models": n,
            "parse_ms": parse["median_ms"],
            "dag_ms": dag["median_ms"],
            "compile_ms": compile_["median_ms"],
            "e2e_ms": e2e["median_ms"],
            "e2e_per_model_ms": round(e2e["median_ms"] / n, 3),
        })

    return results


def run_scale_benchmarks() -> list[dict]:
    """Benchmark synthetic projects at increasing scale."""
    sizes = [10, 50, 100, 200, 500, 1000]
    results = []
    env = _make_env("duckdb")
    sources = ["raw"]

    for n in sizes:
        with tempfile.TemporaryDirectory() as tmp:
            models_dir = Path(tmp)
            _generate_synthetic_models(n, models_dir)
            models = scan_models(models_dir)

            e2e = bench_end_to_end(models, env, sources)
            parse = bench_parse(models)
            dag = bench_dag_pipeline(models, sources)

            results.append({
                "models": n,
                "parse_ms": parse["median_ms"],
                "dag_ms": dag["median_ms"],
                "e2e_ms": e2e["median_ms"],
                "e2e_per_model_ms": round(e2e["median_ms"] / n, 3),
            })

    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_table(title: str, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    widths = {k: max(len(k), *(len(str(r[k])) for r in rows)) for k in keys}

    header = " | ".join(k.rjust(widths[k]) for k in keys)
    sep = "-+-".join("-" * widths[k] for k in keys)

    print(f"\n{'=' * len(header)}")
    print(f" {title}")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)
    for r in rows:
        print(" | ".join(str(r[k]).rjust(widths[k]) for k in keys))
    print()


def print_reddit_format(example_results: list[dict], scale_results: list[dict]) -> None:
    """Print results formatted for a Reddit post (markdown table)."""
    print("\n--- REDDIT-READY MARKDOWN (copy below) ---\n")

    print("### Real-world example projects\n")
    print("| Project | Models | Parse | DAG | Compile | Total | Per model |")
    print("|---------|-------:|------:|----:|--------:|------:|----------:|")
    for r in example_results:
        print(
            f"| {r['project']} | {r['models']} | "
            f"{r['parse_ms']:.2f}ms | {r['dag_ms']:.2f}ms | "
            f"{r['compile_ms']:.2f}ms | **{r['e2e_ms']:.2f}ms** | "
            f"{r['e2e_per_model_ms']:.2f}ms |"
        )

    print("\n### Scale test (synthetic linear DAG)\n")
    print("| Models | Parse | DAG | Total | Per model |")
    print("|-------:|------:|----:|------:|----------:|")
    for r in scale_results:
        print(
            f"| {r['models']} | {r['parse_ms']:.2f}ms | "
            f"{r['dag_ms']:.2f}ms | **{r['e2e_ms']:.2f}ms** | "
            f"{r['e2e_per_model_ms']:.2f}ms |"
        )

    print()


def main() -> None:
    print("Qraft Compilation Benchmark")
    print(f"Python bridge + Rust core (_core)\n")

    print("Running example project benchmarks...")
    example_results = run_example_benchmarks()
    print_table("Example Projects (median of 10 runs, 2 warmup)", example_results)

    print("Running scale benchmarks...")
    scale_results = run_scale_benchmarks()
    print_table("Scale Test — Synthetic Models (median of 10 runs)", scale_results)

    print_reddit_format(example_results, scale_results)


if __name__ == "__main__":
    main()
