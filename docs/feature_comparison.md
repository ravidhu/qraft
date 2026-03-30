# Feature Comparison: Qraft vs dbt Core

A feature-by-feature comparison between Qraft and dbt Core.

---

## Query Reuse Strategies

See [Code Reuse in Qraft](code_reuse.md) for the full analysis, adapter support matrix, and dbt migration guidance. This section summarises the conclusions.

Qraft provides multiple mechanisms for reusing SQL logic across models:

| Strategy | Parameters | DB-agnostic | Status |
|---|---|---|---|
| `{{ var }}` chains | No | Yes | Available |
| DB-native SQL functions | Yes | **No** -- fails on Trino, SQLite | Available (per-adapter) |
| Python macros (`macros/` directory) | Yes | Yes | **Implemented** |
| `qraft-utils` package | Yes | Yes | **Implemented** (local install) |

### Macro system

Python functions in a project's `macros/` directory are expanded at compile time. Models declare which macro modules to use via front-matter (`macros: [utils]`). Macros are database-agnostic, fully parameterized, and composable.

### qraft-utils

A companion package (`qraft-utils`) provides common macros out of the box: `surrogate_key`, `safe_divide`, `cents_to_dollars`, `pivot`, `union_relations`, `date_spine`, and more. It ships as part of the Qraft repository under `python/qraft-utils/` and can be installed locally with `uv pip install ./python/qraft-utils`. PyPI distribution is planned.

### What Qraft does not support (by design)

Qraft does **not** include a Jinja2 template engine or a dbt-style package manager (`dependencies.yaml`). Instead, macros are plain Python functions — simpler to write, test, and debug. To share macros across projects, package them as regular pip packages.

---

## Feature Comparison

### Legend

- **Full** -- Feature-complete, comparable to dbt
- **Partial** -- Basic version exists, missing depth
- **Stub** -- Code skeleton exists, not functional
- **None** -- Not present at all

### Core Modeling

| Feature | dbt Core | Qraft | Gap |
|---------|----------|-------|-----|
| SQL models (`.sql` files) | Full | **Full** | -- |
| `ref()` | Full (+ versioned, cross-project) | **Full** (basic) | No versioning, no cross-project |
| `source()` | Full (+ freshness, tests) | **Full** (basic) | No freshness, no source tests |
| `{{ var() }}` | Full (Jinja, typed, CLI override) | **Partial** | String-only, no CLI `--vars` override, chaining supported |
| Front-matter / config | Full (`config()` block, YAML, project-level) | **Full** (basic) | Supports `materialization`, `schema`, `macros`, `tags`, `description`, `enabled`, `unique_key` |
| Model descriptions/docs | Full (YAML + doc blocks + site) | **Full** | `description` in front-matter, included in manifest. Interactive catalog site via `qraft docs generate/serve`. |

### Materializations

| Materialization | dbt Core | Qraft | Notes |
|-----------------|----------|-------|-------|
| `view` | Full | **Full** | |
| `table` | Full | **Full** | |
| `table_incremental` | Full (5 strategies, `is_incremental()`, schema change handling) | **Full** (append + upsert via `unique_key`, runtime table detection) | |
| `ephemeral` | Full (CTE injection) | **Full** | |
| `materialized_view` | Full | **Full** (Postgres, Trino) | Not available on DuckDB/MySQL |
| `snapshot` (SCD2) | Full (timestamp + check strategies) | **None** | |
| Custom materializations | Full (Jinja macros) | **None** | |

### Templating and Code Reuse

| Feature | dbt Core | Qraft |
|---------|----------|-------|
| Jinja2 (if/else, loops, set) | Full | **None** -- regex replacement only |
| Custom macros | Full (`macros/` dir) | **Full** (Python functions in `macros/` dir) |
| Packages (shared macros/models) | Full (Hub, Git, local) | **Partial** (pip-installable `qraft-utils`) |
| `this` (self-referencing) | Full | **None** |
| `run_query()` (introspection) | Full | **None** |
| Adapter dispatch | Full | **None** |

### Testing

| Feature | dbt Core | Qraft |
|---------|----------|-------|
| Generic data tests (unique, not_null, etc.) | Full (4 built-in + custom) | **Full** (7 built-in: not_null, unique, accepted_values, relationships, number_of_rows, accepted_range, unique_combination_of_columns) |
| Singular data tests | Full (standalone SQL) | **None** |
| Unit tests (mock inputs -> expected output) | Full (v1.8+) | **None** |
| Test packages (dbt-expectations, etc.) | Full | **None** |

### DAG and Selection

| Feature | dbt Core | Qraft | Notes |
|---------|----------|-------|-------|
| Automatic DAG from refs | Full | **Full** | |
| Cycle detection | Full | **Full** | |
| Topological sort -> parallel batches | Full | **Full** | |
| `model+`, `+model`, `+model+` | Full | **Full** | |
| `tag:` selection | Full | **Full** | Tags set via front-matter, selected with `tag:name` |
| `path:` selection | Full | **Partial** | `prefix*` wildcard only |
| `config:` selection | Full | **None** | |
| `state:modified` (Slim CI) | Full | **None** | |
| N-depth selection (`2+model`) | Full | **None** | |
| `@model` (parent intersection) | Full | **None** | |
| Set operators (union, intersect, exclude) | Full | **None** | Single pattern only |
| YAML selectors (named, reusable) | Full | **None** | |

### Validation and Governance

| Feature | dbt Core | Qraft |
|---------|----------|-------|
| Missing ref detection | Full | **Full** |
| Missing source detection | Full | **Full** |
| Fuzzy typo suggestions | None (just errors) | **Full** (Jaro-Winkler) -- Qraft is better here |
| Model contracts (enforced schema) | Full | **None** |
| Column constraints | Full | **None** |
| Model versioning | Full | **None** |
| Groups + access modifiers | Full | **None** |

### Operations and Lifecycle

| Feature | dbt Core | Qraft |
|---------|----------|-------|
| Seeds (CSV -> table) | Full | **None** |
| Source freshness monitoring | Full | **None** |
| Hooks (pre/post/on-run) | Full | **None** |
| Exposures (downstream tracking) | Full | **None** |
| Metrics / Semantic Layer | Full (MetricFlow) | **None** |
| Artifacts (manifest, catalog, results) | Full | **Partial** (manifest.json with nodes, DAG, sources, batches) |
| `retry` (re-run failures) | Full | **None** |
| Partial parsing | Full | **None** |

### Database Support

| Feature | dbt Core | Qraft |
|---------|----------|-------|
| Adapter interface | Full (abstract, pluggable) | **Full** (abstract Engine class) |
| DuckDB | Community adapter | **Full** |
| Postgres | First-party | **Full** |
| MySQL/MariaDB | First-party | **Full** |
| Trino | Community adapter | **Full** |
| Snowflake, BigQuery, Redshift, etc. | First-party | **None** (accessible as read-only sources via Trino connectors or DuckDB extensions) |
| Community adapters (30+) | Full ecosystem | **None** |
| Cross-database reads | Full (via adapters) | **Partial** (single-engine; reads via DuckDB extensions or Trino connectors) |

### CLI

| Command | dbt Core | Qraft |
|---------|----------|-------|
| `init` | Full | **Full** |
| `compile` | Full | **Full** |
| `run` | Full | **Full** |
| DAG visualization | `docs serve` (interactive web) | **Full** (interactive catalog app + text-based `dag` command) |
| `validate` | `parse` + `debug` | **Full** (dedicated command) |
| `clean` | Removes build artifacts | **Full** (drops DB objects -- more useful) |
| `test-connection` | `debug` | **Full** (dedicated) |
| `test` | Full | **Full** (generic data tests from front-matter) |
| `build` (run + test + seed + snapshot) | Full | **Partial** (run + test, no seed/snapshot) |
| `seed` | Full | **None** |
| `snapshot` | Full | **None** |
| `docs generate/serve` | Full | **Full** (interactive React catalog with lineage, model details, test results) |
| `source freshness` | Full | **None** |
| `list` | Full | **None** |
| `retry` | Full | **None** |
| `show` (preview results) | Full | **Full** (compiled SQL + `--expanded` for post-macro) |
| `run-operation` | Full | **None** |

### Performance

| Aspect | dbt Core | Qraft |
|--------|----------|-------|
| Parsing speed | Python (slow on large projects) | **Rust** (significantly faster) |
| DAG operations | Python (networkx) | **Rust** (petgraph, faster) |
| Compilation | Jinja2 Python rendering | **Rust** batch compile |
| Orchestration | Python threading | **Python** multiprocessing (true parallelism) |
| Startup time | Slow (full Jinja parse) | **Fast** (compiled extension) |

---

## Summary Scorecard

| Category | dbt Core Features | Qraft Has | Coverage |
|----------|-------------------|-----------|----------|
| Core modeling (ref, source, var) | 6 | 5 | ~83% |
| Materializations | 6 | 5 | ~83% |
| Templating / code reuse | 6 | 2 | ~33% |
| Testing | 4 | 1 | 25% |
| DAG and selection | 10 | 5 | 50% |
| Validation | 6 | 3 | 50% |
| Operations and lifecycle | 8 | 1 | ~13% |
| Database adapters | 7+ | 4 | ~57% |
| CLI commands | 15 | 11 | ~73% |
| Performance | Baseline | Faster | Advantage |

**Overall feature coverage: ~49% of dbt Core.**

---

## Where Qraft Wins

- **Performance** -- Rust core is meaningfully faster for parsing, compilation, and DAG operations
- **Fuzzy suggestions** -- Better DX than dbt for typo detection in refs and sources
- **Simplicity** -- No Jinja complexity, no `profiles.yml` vs `dbt_project.yml` confusion, single config file
- **Clean command** -- Drops actual DB objects (dbt clean only removes local artifacts)
- **Dedicated validate command** -- One command to check everything with actionable suggestions

---

## Critical Gaps to Close for Production Adoption

Listed in priority order:

1. ~~**Incremental materialization**~~ -- Done. `table_incremental` with upsert via `unique_key`.
2. ~~**Testing framework**~~ -- Done. 7 built-in generic data tests (`not_null`, `unique`, `accepted_values`, `relationships`, `number_of_rows`, `accepted_range`, `unique_combination_of_columns`) with `qraft test` and `qraft build` commands.
3. ~~**Ephemeral materialization**~~ -- Done. Ephemeral models compile to CTEs.
4. ~~**Macros**~~ -- Done. Python macro system with `qraft-utils` package.
5. **Seeds** -- Loading reference data from CSV files.
6. ~~**At least one more adapter**~~ -- Done. PostgreSQL, MySQL/MariaDB, and Trino adapters implemented.

---

## Features to Deliberately Skip

These add complexity without proportional value for an early-stage tool:

- **Full Jinja2** -- Complexity trap. Consider MiniJinja for a focused subset instead.
- **Semantic Layer / MetricFlow** -- Separate concern, better as a standalone tool.
- **Model versioning, groups, access modifiers** -- Enterprise governance features, premature for v0.x.
- **Exposures** -- Nice-to-have for lineage, not critical for core workflows.
- **Cross-project refs / dbt Mesh** -- Multi-project orchestration is premature.
- **Custom materializations** -- Focus on getting the built-in ones right first.
