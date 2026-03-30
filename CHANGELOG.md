# Changelog

All notable changes to Qraft are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-03-30

### Added

#### .env.example Improvements
- Updated `.env.example` template with standard database connection variables (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`)
- Applied to root, example projects, and `qraft init` scaffold

#### Publishing Scripts
- `scripts/publish_testpypi.sh` — publish qraft and qraft-utils to TestPyPI
- `scripts/publish_pypi.sh` — publish to production PyPI (with confirmation prompt)
- Both scripts auto-install required tools (`twine`, `build`, `maturin`) via `uv tool install`
- Makefile targets: `publish`, `publish-qraft`, `publish-utils`, `publish-testpypi`, `publish-testpypi-qraft`, `publish-testpypi-utils`

#### Open Source Preparation
- Config validation: `project.yaml` is now validated on load with clear error messages for missing/invalid fields
- `.pyi` type stubs for the Rust `_core` module (IDE autocompletion and type checking)
- Public Python API: key functions exported from `qraft.__init__` (`load_config`, `run`, `compile_model`, etc.)
- `CONTRIBUTING.md` at repo root (standard GitHub convention)
- Engine support matrix in materialization types documentation
- `docs generate` / `docs serve` fully documented in CLI reference
- DuckDB parallel limitation documented (auto-capped to 1)
- Mermaid diagrams: compilation pipeline (README), config resolution flow, engine class hierarchy, macro expansion lifecycle, test execution flow, model execution sequence
- "Why Qraft?" document (`docs/why_qraft.md`)
- dbt migration guide (`docs/migrating_from_dbt.md`)
- `ROADMAP.md` with phased release plan
- `qraft-utils` package prepared for PyPI: metadata, README, classifiers, project URLs
- Docstrings on all public bridge functions and `Engine` abstract base class

#### Open Source Readiness
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- SECURITY.md with vulnerability reporting policy
- GitHub issue templates (bug report, feature request)
- GitHub pull request template
- GitHub FUNDING.yml for sponsorship
- PyPI metadata: classifiers, keywords, project URLs, full author info
- Cargo.toml metadata: description, repository, license, authors

#### Catalog / Documentation Site
- `qraft docs generate --env <env>` command to build interactive catalog site from manifest
- `qraft docs serve` command to start local HTTP server for viewing the catalog
- Interactive DAG lineage visualization with pan, zoom, and click-to-inspect (React + @xyflow/react)
- Collapsible sidebar with file-tree model explorer and search
- Bottom detail panel with SQL (compiled/raw), dependencies, and test results tabs
- Model nodes colored by materialization type (view, table, incremental, ephemeral, source)
- Pre-built React SPA shipped with the Python package (no Node.js required at runtime)
- Catalog app source in `catalog_app/` (Vite + React + TypeScript + shadcn/ui)
- `make build-catalog` target to rebuild the catalog app

#### Testing Framework
- Generic data tests: 7 built-in test types (`not_null`, `unique`, `accepted_values`, `relationships`, `number_of_rows`, `accepted_range`, `unique_combination_of_columns`)
- Test definitions in model front-matter via `columns:` block with per-column `description` and `tests`
- `qraft test --env <env>` CLI command to run data tests
- `qraft build --env <env>` CLI command (run models then tests in DAG order)
- Test configuration: `severity` (`error`/`warn`) and `where` clause filtering per test
- `--fail-fast` flag to stop on first test failure
- `--select` support for filtering which models' tests run
- `Engine.query()` method on all engines (DuckDB, PostgreSQL, MySQL, Trino) for result-returning queries
- Test result reporting with pass/fail counts and failing row samples
- `target/test_results.json` output with structured test results for CI/CD integration
- Dedicated testing documentation (`docs/testing.md`) with detailed explanations of each built-in test type

#### Core Architecture
- Hybrid Rust/Python architecture: Rust core (PyO3) for parsing, DAG, and compilation; Python for CLI, config, and orchestration
- Regex-based SQL parser for `{{ ref('...') }}`, `{{ var('...') }}`, and model front-matter extraction
- DAG construction with petgraph: topological sorting (Kahn's algorithm), cycle detection, and missing-ref detection with fuzzy suggestions (strsim/Jaro-Winkler)
- Model selector supporting patterns: `model_name`, `model+`, `+model`, `+model+`, `tag:name`, `prefix*`

#### SQL Compilation
- Materialization types: `view`, `table`, `ephemeral` (CTE injection)
- Materialized view support
- Incremental materialization with `unique_key` upsert and `{% if is_incremental() %}` block support
- Variable substitution chains (`{{ var('key') }}`) with environment-level overrides, configurable max passes via `QRAFT_MAX_VAR_PASSES` env var (default: 10)
- `{{ ref('model') }}` resolution to `schema.model_name`
- DDL generation per materialization type

#### Macro System
- Python-based pre-compilation macro system (not Jinja2)
- Rust macro call parser for extracting call sites with parenthesis balancing
- Python macro expander and loader: models declare `macros: [module_name]` in YAML front-matter
- Macro pipeline: refs/vars resolved -> macros expanded -> DDL generated
- `qraft-utils` pip-installable macro utility library with modules: conditions, date, scalar, structural

#### Database Engines
- Abstract `Engine` class with pluggable implementations
- DuckDB engine (built-in, zero-config)
- PostgreSQL engine via `psycopg`
- MySQL/MariaDB engine via `pymysql`
- Trino engine with catalog/schema configuration

#### CLI
- Commands: `init`, `compile`, `run`, `dag`, `validate`, `clean`, `test-connection`, `show`
- Built with `click` and `rich` for terminal formatting
- Model selection patterns for targeted compilation and execution

#### Configuration
- Single `project.yaml` as source of truth
- Deep merging for per-environment overrides
- Environment variable substitution (`${VAR_NAME}`)
- Per-environment connection, schema, materialization, and variable settings
- `.env` file support via `python-dotenv`

#### Execution
- DAG-aware batching: models in the same topological layer run concurrently
- Compiled SQL output to `target/compiled/<env>/*.sql`
- Batch-parallel execution via `multiprocessing.ProcessPoolExecutor`

#### Manifest
- Manifest generation (`manifest.json`) with nodes, DAG edges, sources, and batch info
- `manifest.py` module and tests for pipeline metadata output
- Rust DAG builder exposes edge/source data for manifest consumption

#### Developer Experience
- `make dev` for rapid Rust recompilation + Python dev install (maturin)
- `make test` for full test suite (Rust + Python)
- `make lint` for clippy, rustfmt, ruff, and mypy
- Example projects: `ecommerce_basic`, `saas_analytics`
- `blog_analytics` and `datalakehouse_trino` examples
- Docker Compose files for example database setups
- `scripts/benchmark.py` — compilation pipeline benchmark across example projects and synthetic scale tests

#### Documentation
- Architecture overview, CLI reference, configuration guide
- Code reuse and macro authoring guide
- Contributing guide with engine extension instructions
- Feature comparison against dbt Core
- Compilation benchmarks (`docs/benchmarks.md`) with real-world and scale test results

### Changed
- Renamed cryptic variables across Python and Rust codebase for junior-engineer readability: `e`→`error`, `r`→`test_result`/`model_result`, `m`→`model`, `pm`→`parsed_model`, `fm`→`front_matter_content`, `mat`→`materialization`, `src`→`source_config`, `vars_`→`current_variables`, `fn`→`macro_function`, `c`→`compiled_model`, `n`→`node`, and more (20 findings across 22 files)
- README: expanded feature list (data testing, model selection, catalog, dry-run, front-matter), added link to "Why Qraft?"
- `docs/why_qraft.md`: refined tone and wording throughout, removed "smaller ecosystem" caveat
- `docs/configuration.md`: `schema` field is now optional (default: `public`), clarified connection merge behavior, corrected test parameter names (`min`/`max` aliases, `columns` alias)
- `docs/testing.md`: all CLI examples now include required `--env` flag
- `docs/cli_reference.md`: added `--fail-fast` option to `test` and `build` commands, expanded `build` options table
- `docs/code_reuse.md`: documented mandatory `vars` keyword argument on macros
- `qraft-utils` README: corrected `recency()` signature to `recency(date_column, days)`
- Removed ADR references from public-facing docs (ADRs are internal records, not published)
- `qraft-utils` install documentation updated with PyPI, local path, and copy-to-macros options
- README: added compilation pipeline diagram, testing docs link, new documentation links
- `qraft init .` support to initialize a project in the current directory
- Expanded installation docs with local dependency and wheel build instructions
- Architecture diagram replaced with Mermaid block-beta with Python/Rust color coding and component summary table
- CLI reference updated: batch compilation flow, `tag:name` selector, `macros/` directory in `init`, `dag` command clarification
- Code reuse guide updated: `generate_surrogate_key` macro, `QRAFT_MAX_VAR_PASSES` env var, `star_except` requirements, engine-aware vars injection
- Consolidated model selection into `build_pipeline()`: optional `select` parameter applies filtering inside Rust, eliminating a separate boundary crossing
- Batch compilation: `batch_compile()` resolves all models in one Rust call, expands macros in Python, then batch-wraps DDL — reducing compilation from 2N boundary crossings to 2
- Consolidated DAG pipeline into single Rust call: `build_pipeline()` performs parse, build, validate, and sort in one boundary crossing instead of 2N+3
- CLI commands (`compile`, `run`, `validate`, `dag`) now use `build_pipeline()` for the DAG phase
- Runner validates DAG during pipeline build and exits early on errors
- Orchestration moved from Rust to Python runner for flexibility and debuggability
- Removed `rust/src/orchestrator/` module; Python `runner.py` now owns execution logic
- Simplified CLI by delegating orchestration to Python layer
- Engine module reorganized with `__init__.py` factory for engine instantiation
- Expanded engine connection parameters: Trino (`schema`, `http_scheme`, `roles`), PostgreSQL (`sslmode`), MySQL (`charset`, `ssl`)
- Configuration and concepts docs updated with full parameter tables, all materialization types, and front-matter reference
- Renamed doc files from hyphens to underscores (`cli-reference` → `cli_reference`, etc.) and updated all cross-references
- Renamed `roadmap.md` to `feature_comparison.md` with updated title and content
- Removed GitHub Actions workflows (ci.yml, release.yml)
- Fixed `.gitignore` to stop ignoring `.github/` directory
- Replaced placeholder `your-org` URLs with `ravidhu/qraft` in docs

### Fixed
- Config validation no longer rejects unknown engine types (e.g. `snowflake`, `bigquery`) at load time — unknown engines are now allowed and only fail at runtime when `get_engine()` is called, enabling extensibility
- PostgreSQL engine now accepts `database` config key (previously only `dbname` worked)
- Table incremental materialization bug
