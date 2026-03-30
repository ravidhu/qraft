# CLAUDE.md

## Project Overview

Qraft is a lightweight SQL templating and orchestration tool — a fast, minimal alternative to dbt. It has a Rust core (parsing, DAG, compilation) exposed to Python via PyO3, with Python handling CLI, config, database engines, and orchestration.

## Python

Always use `uv` to run Python commands. Never use `python`, `python3`, or `pip` directly.

- Use `uv run` instead of `python` or `python3` (e.g., `uv run pytest`, `uv run python script.py`)
- Use `uv pip` instead of `pip`
- Use `uv sync` to install dependencies from pyproject.toml

## Build & Development

This is a hybrid Rust/Python project built with maturin. After ANY Rust code change, you must rebuild:

```bash
make dev          # Compile Rust + install in dev mode (maturin develop)
```

## Testing

```bash
make test         # Run all tests (Rust + Python)
make test-rust    # Rust tests only (cargo test)
make test-python  # Python tests only (auto-runs make dev first)
```

Python tests live in `python/qraft/tests/` and use pytest. Rust tests are collocated with source (e.g., `parser.rs` + `parser_tests.rs`).

## Linting

```bash
make lint         # Run all linters
```

This runs: `cargo clippy -- -D warnings`, `cargo fmt -- --check`, `ruff check python/`, `mypy python/qraft/`

## Project Structure

- `rust/src/` — Rust core: SQL parsing (regex-based), DAG (petgraph), compilation, model selection
- `python/qraft/` — Python package: CLI (click), config (YAML), engines, runner, macros
- `python/qraft-utils/` — Pip-installable macro utility library
- `examples/` — Example projects (blog_analytics, ecommerce_basic, saas_analytics, datalakehouse_trino)
- `docs/` — Documentation

## Architecture

- **Rust** handles compute-intensive work: SQL parsing, DAG building/validation/sorting, compilation
- **Python** handles I/O: CLI, config loading, database connections, orchestration, macro expansion
- Bridge modules (`compiler/bridge.py`, `dag/bridge.py`) are thin wrappers — business logic belongs in Rust
- The compiled Rust module is imported as `qraft._core`

## Key Conventions

- Python: PEP 8, type annotations on all function signatures, dataclasses for config types, ruff + mypy enforced
- Rust: standard conventions, doc comments on public functions, thiserror for errors, clippy warnings are errors
- PyO3 glue lives in `rust/src/lib.rs`; core logic stays in submodules
- Test files: `test_*.py` (Python), `*_tests.rs` (Rust, collocated)

## Tech Stack

- Python >=3.11, Rust edition 2021
- Build: maturin
- CLI: click, rich
- Config: pyyaml, python-dotenv
- Rust deps: pyo3, regex, petgraph, strsim, thiserror
- Database engines: duckdb (built-in), psycopg (postgres), pymysql (mysql), trino
- Parallelism: multiprocessing.ProcessPoolExecutor for batch execution
