# Why Qraft?

A fast, minimal SQL templating and orchestration tool with a Rust core built for data engineers who want speed, simplicity, and Python-native tooling without the complexity of a full-featured transformation framework.

## Performance where it matters

Qraft's core — SQL parsing, DAG construction, topological sorting, and compilation — is written in Rust and exposed to Python via PyO3. I made this decision to leverage Rust's performance. Parsing hundreds of SQL files, resolving dependencies, and compiling templates are CPU-bound operations that benefit directly from Rust's speed and efficient memory management.

The bridge between Python and Rust is designed to minimize overhead. Batch compilation sends all models to Rust in 2-3 calls rather than 2N individual round trips. The result: compilation time stays near-constant as your project grows, instead of scaling linearly with model count.

Execution uses Python's `multiprocessing.ProcessPoolExecutor` for true parallelism. Independent models in the DAG run concurrently across CPU cores, not sequentially or in cooperative coroutines.

## Simplicity by design

A Qraft project has one configuration file: `project.yaml`. There is no separate `profiles.yml`, no `dbt_project.yml`, no `packages.yml`. Database connections, project settings, and model paths all live in one place.

SQL models are plain SQL with a small set of built-in functions:

- `ref('model_name')` to reference other models
- `source('source_name')` to reference raw tables
- `{{ var }}` for variable substitution

There is no Jinja2. No `{% if %}` blocks, no `{% for %}` loops, no `{% macro %}` definitions inside SQL files. If you need conditional logic or code generation, you write a Python function and call it as a macro. This is a deliberate trade-off: less power inside templates, more clarity about what your SQL actually does. For me, that makes SQL easier to read, with Python available for more complex logic when needed.

## Developer experience

Qraft provides tooling that catches problems early and makes debugging straightforward.

**Fuzzy matching for typos.** If you write `ref('ordres')` when the model is named `orders`, Qraft uses Jaro-Winkler similarity to suggest the correct name. This applies to both `ref()` and `source()` calls.

**Validation before execution.** The `qraft validate` command parses all models, builds the DAG, checks for cycles, and verifies that all references resolve — without touching any database. Run it in CI to catch breakage before it reaches production.

**Macro debugging.** The `qraft show --expanded` command renders a model with all macros expanded, so you can see the exact SQL that will be sent to your database engine.

**Clear error messages.** When something fails, Qraft tells you which model, which line, and what went wrong. No stack traces through template rendering internals.

## Python-native macros

Macros in Qraft are plain Python functions. You write them in `.py` files, import standard libraries, use type hints, and test them with pytest. There is no new language to learn, or if there is, it's just Python.

```python
def date_spine(start: str, end: str, interval: str = "day") -> str:
    return f"SELECT generate_series('{start}'::date, '{end}'::date, '1 {interval}'::interval) AS date_day"
```

Macros can be engine-aware, adapting their output based on which database you are targeting. A macro that generates date functions can emit `DATE_TRUNC` for PostgreSQL and `date_trunc` for DuckDB without the model author needing to think about it.

Because macros are Python packages, you can version them, publish them to PyPI, and install them with pip. Shared macro libraries work the same way as any other Python dependency.

## Multi-engine support

Qraft supports multiple database engines out of the box:

- **DuckDB** — built-in, no external database required. Useful for local development and testing.
- **PostgreSQL** — via psycopg.
- **MySQL / MariaDB** — via pymysql.
- **Trino** — for federated queries across data sources.

Cross-database reads are possible through DuckDB extensions (e.g., the PostgreSQL scanner) or Trino's connector architecture. You can develop locally against DuckDB and deploy to PostgreSQL or Trino without rewriting your models, as long as your SQL is compatible.

## Built-in testing

Tests in Qraft are defined directly in a model's SQL front-matter. There is no separate YAML schema file to maintain alongside your SQL.

Qraft supports seven test types: not-null, unique, accepted values, relationships, row count, custom SQL expressions, and custom query tests. Each test is declared in the model file where the tested column is defined, keeping the assertion close to the code it validates.

## Modern materializations

Qraft supports five materialization strategies:

- **view** — creates or replaces a database view.
- **table** — creates or replaces a table via `CREATE TABLE AS`.
- **ephemeral** — injects the model as a CTE into downstream models. No database object is created.
- **table_incremental** — appends or upserts data into an existing table, with configurable merge keys.
- **materialized_view** — creates a materialized view where the database engine supports it.

## Interactive catalog

The `qraft docs generate` command produces a self-contained React single-page application with interactive DAG visualization. Run `qraft docs serve` to browse your project's model lineage, inspect dependencies, and explore documentation locally. The catalog is a static build that can be deployed to any web server or shared as a directory.

## What Qraft is not

Qraft is not a full replacement for dbt, yet ;). If your team depends on features from the broader dbt ecosystem, you should be aware of what Qraft does not provide:

- **No Jinja2 templating.** If your project relies heavily on Jinja control flow inside SQL, migrating to Qraft means rewriting that logic as Python macros or simplifying your models.
- **No snapshots.** Qraft does not have a built-in slowly changing dimension (SCD) mechanism.
- **No seeds.** There is no built-in CSV-to-table loading. Use your database's native import tools or a Python script.
- **No semantic layer.** Qraft does not define or serve metrics.

## Who is Qraft for?

Qraft is a good fit if:

- You want fast compilation and execution, and your current tool is the bottleneck.
- You prefer writing Python over Jinja2 for reusable logic.
- You value a simple project structure with minimal configuration.
- You want to test your macros and transformations with standard Python testing tools.

If that describes your team, give Qraft a try. It is a focused tool that does less, but does it well.
