# Contributing

## Prerequisites

- **Python 3.11+**
- **Rust toolchain** -- Install via [rustup](https://rustup.rs/)
- **uv** -- Python package and project manager
- **maturin** -- `uv pip install maturin`

## Development Setup

```bash
# Clone the repository
git clone https://github.com/ravidhu/qraft.git
cd qraft

# Install Python dependencies
uv sync

# Build the Rust extension and install in dev mode
make dev
```

`make dev` runs `maturin develop`, which compiles the Rust crate and installs it as `qraft._core` in your virtual environment. You need to re-run this after any Rust code changes.

See [Architecture](docs/architecture.md) for the full project structure and how modules fit together.

## Running Tests

```bash
# All tests (Rust + Python)
make test

# Rust tests only
make test-rust

# Python tests only
make test-python

# Run a specific test file
uv run pytest python/qraft/tests/test_compiler_bridge.py -v

# Run a specific test
uv run pytest python/qraft/tests/test_dag_bridge.py::TestTopoSort -v
```

`make test-python` automatically runs `make dev` first to ensure the Rust extension is up to date.

## Linting

```bash
make lint
```

This runs:
- `cargo clippy` -- Rust linter (warnings treated as errors)
- `cargo fmt --check` -- Rust formatting check
- `ruff check` -- Python linter
- `mypy` -- Python type checking

## Code Style

### Rust
- Follow standard Rust conventions (`cargo fmt`)
- All public functions should have doc comments (`///`)
- Use `thiserror` for error types
- Keep PyO3-specific code in `lib.rs`; keep core logic in submodules
- Rust tests are collocated: `parser.rs` + `parser_tests.rs`

### Python
- Follow PEP 8 (enforced by ruff)
- Use type annotations for function signatures
- Dataclasses for config types
- Bridge modules should be thin wrappers -- business logic belongs in Rust
- Python tests live in `python/qraft/tests/` and use pytest

## Adding a New Database Engine

1. Create `python/qraft/engine/<name>_engine.py`
2. Implement the `Engine` abstract class from `python/qraft/engine/base.py`
3. Register it in the `get_engine()` factory in `python/qraft/engine/__init__.py`
4. Add the client library as an optional dependency in `pyproject.toml` (e.g., `[project.optional-dependencies]`)
5. Add tests in `python/qraft/tests/`

## Making Changes

### Rust changes

1. Edit files under `rust/src/`
2. Run `make dev` to recompile
3. Run `make test-rust` for Rust-only tests
4. Run `make test` for full test suite

### Python changes

1. Edit files under `python/qraft/`
2. Run `make test-python` (no recompile needed unless you changed Rust code)

### Adding a new Rust function exposed to Python

1. Implement the function in the appropriate Rust module
2. Add a `#[pyfunction]` wrapper in `rust/src/lib.rs`
3. Register it in the `#[pymodule]` function
4. Create or update the Python bridge in `python/qraft/*/bridge.py`
5. Add tests on both sides

## Running Examples

```bash
# Seed the database with test data
duckdb examples/ecommerce_basic/dev.duckdb < examples/ecommerce_basic/seeds/seed.sql

# Run the models
uv run qraft run --env local --project examples/ecommerce_basic

# View the DAG
uv run qraft dag --project examples/ecommerce_basic
```

## Documentation

- Update relevant docs when changing user-facing behavior
- Update `CHANGELOG.md` with notable changes
