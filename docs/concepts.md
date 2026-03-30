# Core Concepts

## Models

A model is a SQL file inside the `models/` directory. Each file produces one database object (a view or a table). The filename (without `.sql`) becomes the model name.

```
models/
  stg_customers.sql    → model name: stg_customers
  stg_orders.sql       → model name: stg_orders
  customer_summary.sql → model name: customer_summary
```

Models can be organized in subdirectories for readability. A common convention is the bronze/silver/gold pattern:

```
models/
  bronze/    # Staging: clean and rename raw data
  silver/    # Intermediate: join and enrich
  gold/      # Business-facing: facts and dimensions
```

Subdirectories are organizational only -- the model name is always the filename.

## References (refs)

Models reference each other using `ref('model_name')`. This tells Qraft that one model depends on another.

```sql
-- models/customer_summary.sql
SELECT * FROM ref('stg_customers') c
JOIN ref('stg_orders') o ON c.customer_id = o.customer_id
```

At compile time, `ref('stg_customers')` resolves to `analytics.stg_customers` (using the configured schema). This also registers a dependency edge in the DAG.

## Sources

Sources represent external tables that exist outside your Qraft project (raw data, third-party tables). They are declared in `project.yaml` under the `sources` key, and referenced in SQL with `source('<source_key>', '<table>')`, where `<source_key>` matches the key in your config.

```yaml
# project.yaml
sources:
  raw:
    schema: raw_data
    tables:
      - customers
      - orders
```

```sql
-- models/stg_customers.sql
SELECT * FROM source('raw', 'customers')
-- Resolves to: raw_data.customers
```

For engines that use catalogs (e.g., Trino), add the `database` field to produce a fully qualified `catalog.schema.table` reference:

```yaml
sources:
  lake:
    database: hive          # catalog name
    schema: raw_events
    tables:
      - pageviews
```

```sql
SELECT * FROM source('lake', 'pageviews')
-- Resolves to: hive.raw_events.pageviews
```

## Cross-Database Access

Qraft uses a **single-engine architecture**: one primary database connection handles all SQL execution. There is no multi-engine orchestration where one engine reads and another writes within the same run.

Cross-database reads are achieved by leveraging the **primary engine's own cross-database capabilities**:

- **DuckDB** can attach external databases (PostgreSQL, MySQL, SQLite) as read-only sources using its built-in extensions and `init_sql`
- **Trino** can query across multiple catalogs (Hive, Iceberg, PostgreSQL, MySQL, etc.) natively via its connector architecture

Sources declared in `project.yaml` are resolved at compile time into fully qualified table names (e.g., `pg.raw_data.customers` or `hive.raw_events.pageviews`). The primary engine must be able to resolve and query those names — Qraft does not open separate connections to source databases.

### Example: Reading PostgreSQL from DuckDB

DuckDB attaches a PostgreSQL database as a read-only foreign source. Models read from PostgreSQL tables and write results to DuckDB.

```yaml
connection:
  type: duckdb
  path: analytics.duckdb
  init_sql: "INSTALL postgres; LOAD postgres; ATTACH 'postgresql://user:pass@host:5432/db' AS pg (TYPE POSTGRES, READ_ONLY)"

sources:
  app:
    database: pg
    schema: public
    tables: [users, orders]
```

```sql
-- models/stg_users.sql
SELECT * FROM source('app', 'users')
-- Resolves to: pg.public.users (read from PostgreSQL via DuckDB)
```

See the [postgres_to_duckdb example](../examples/postgres_to_duckdb/) for a complete working setup.

### Example: Cross-Catalog Queries with Trino

Trino accesses multiple catalogs natively. Sources can reference different catalogs while the primary connection writes to a single target catalog.

```yaml
connection:
  type: trino
  host: trino.example.com
  catalog: iceberg

sources:
  lake:
    database: hive
    schema: raw_events
    tables: [pageviews, signups]
  crm:
    database: postgres
    schema: salesforce
    tables: [accounts, contacts]
```

### What is not supported

- **Multi-engine writes** — You cannot read from PostgreSQL and write to BigQuery in a single run. All models are materialized by the primary engine.
- **BigQuery, Snowflake, Redshift** — No native engine adapters exist for these databases. However, if Trino has a connector configured for them, you can read from them as sources through the Trino engine.

## Variables

Variables let you inject configuration values into SQL. Declare them in `project.yaml` and reference them with `{{ variable_name }}`.

```yaml
vars:
  min_order_amount: "0"
```

```sql
WHERE order_total >= {{ min_order_amount }}
-- Resolves to: WHERE order_total >= 0
```

Variables can be overridden per environment, making the same SQL work differently in dev vs. prod.

Variables can also reference other variables (chaining). The resolver runs multiple passes until all references are resolved. See [Code Reuse](code_reuse.md) for details.

## The DAG

Qraft builds a Directed Acyclic Graph (DAG) from all `ref()` calls. Each model is a node, and each `ref()` creates an edge.

```
source(raw.customers) → stg_customers ─┐
                                        ├→ customer_summary
source(raw.orders)    → stg_orders    ─┘
```

The DAG determines:

1. **Execution order** -- Models run only after their dependencies complete
2. **Parallel batches** -- Independent models in the same "layer" run concurrently
3. **Validation** -- Cycles and missing references are caught before execution

### Batches

Topological sort groups models into batches. Within a batch, all models are independent and can run in parallel.

```
Batch 0: [stg_customers, stg_orders]        ← run in parallel
Batch 1: [customer_summary]                  ← depends on batch 0
```

## Materialization

Each model produces a database object. The default materialization is set in `project.yaml` and can be overridden per model using YAML front-matter.

```yaml
# project.yaml
materialization: view   # Default for all models
```

```sql
---
materialization: table
---
SELECT ...
```

| Materialization | DDL Generated | Use Case |
|----------------|---------------|----------|
| `view` | `CREATE OR REPLACE VIEW` | Lightweight transformations, always fresh |
| `table` | `DROP TABLE IF EXISTS; CREATE TABLE AS` | Expensive queries, queried frequently |
| `ephemeral` | No DDL — injected as CTE into downstream models | Reusable logic, not materialized |
| `materialized_view` | `CREATE MATERIALIZED VIEW IF NOT EXISTS` | Pre-computed views (Postgres, Trino) |
| `table_incremental` | `INSERT INTO` (with optional `DELETE` for upsert) | Append-only or upsert patterns |

For `table_incremental`, set `unique_key` in front-matter to enable upsert (delete + insert):

```sql
---
materialization: table_incremental
unique_key: order_id
---
SELECT * FROM source('raw', 'orders')
WHERE updated_at >= CURRENT_DATE - INTERVAL '3 days'
```

## Front-matter

Models can include YAML front-matter between `---` delimiters to override settings:

```sql
---
materialization: table
schema: custom_schema
macros: [utils, date_helpers]
tags: staging, daily
description: Cleaned customer data
enabled: true
unique_key: customer_id
---
SELECT ...
```

| Field | Description |
|-------|-------------|
| `materialization` | Override the default materialization |
| `schema` | Override the target schema for this model |
| `macros` | Comma-separated list of macro modules to load |
| `tags` | Comma-separated tags for selection with `tag:name` |
| `description` | Model description (included in manifest) |
| `enabled` | Set to `false` to skip this model |
| `unique_key` | Column for upsert logic in `table_incremental` |
| `columns` | Column descriptions and data test definitions (see [Testing](#testing)) |

## Environments

Environments let you configure different settings for different deployment targets. You define a base configuration and override specific fields per environment.

```yaml
# Base config (applies to all environments)
schema: analytics
materialization: view
vars:
  min_amount: "0"

environments:
  local:
    # Inherits everything from base
  staging:
    schema: analytics_staging
  prod:
    schema: analytics_prod
    connection:
      type: postgres
      host: prod-db.example.com
    vars:
      min_amount: "100"
```

When you run `qraft run --env prod`, the base config is deep-merged with the `prod` overrides. See [Configuration](configuration.md) for the full merge behavior.

## Selection Patterns

You can run or compile a subset of models using the `--select` option. Patterns support exact match, ancestor/descendant traversal (`+model`, `model+`), tag filtering (`tag:name`), and prefix wildcards (`prefix*`).

```bash
qraft run --env local --select "stg_orders+"
# Runs stg_orders and everything downstream of it
```

See [CLI Reference — Selection Patterns](cli_reference.md#selection-patterns) for the full pattern syntax.

## Target Directory

When you compile or run, Qraft writes resolved SQL files to `target/compiled/<env>/` and generates a `target/manifest.json` with model metadata and dependency graph:

```
target/
  compiled/
    local/
      stg_customers.sql
      stg_orders.sql
      customer_summary.sql
  manifest.json
  test_results.json
```

The compiled SQL files contain the fully resolved SQL — useful for debugging, auditing, or version control. The manifest contains model metadata, DAG edges, sources, and batch ordering. The `test_results.json` is written after `qraft test` or `qraft build` with structured pass/fail results (see [Testing](testing.md#test-results-output)).

## Testing

Qraft includes a built-in data testing framework. Tests are defined in model front-matter inside a `columns:` block and run with `qraft test` or `qraft build`. Each test generates a SQL query where **rows returned = failures**.

```sql
---
columns:
  - name: customer_id
    tests:
      - not_null
      - unique
  - name: status
    tests:
      - accepted_values:
          values: [pending, shipped, delivered]
---
SELECT ...
```

Seven built-in test types are available: `not_null`, `unique`, `accepted_values`, `relationships`, `accepted_range`, `number_of_rows`, and `unique_combination_of_columns`.

For detailed documentation on each test type -- including parameters, generated SQL, configuration options, and examples -- see **[Testing](testing.md)**.

## Compilation Pipeline

When Qraft compiles a model, it applies transformations in this order:

1. **Extract front-matter** -- Parse and remove the YAML block
2. **Parse** -- Identify all `ref()`, `source()`, and `{{ }}` expressions
3. **Resolve refs** -- Replace `ref('name')` with `schema.name` (or inject CTE for ephemeral)
4. **Resolve sources** -- Replace `source('name', 'table')` with `[database.]schema.table`
5. **Resolve variables** -- Replace `{{ var }}` with the configured value
6. **Expand macros** -- Replace macro calls with their SQL output
7. **Generate DDL** -- Wrap the SQL in the appropriate statement (`CREATE VIEW`, `CREATE TABLE AS`, `INSERT INTO`, etc.)

The result is a `CompiledModel` containing both the resolved SQL body and the full DDL statement.
