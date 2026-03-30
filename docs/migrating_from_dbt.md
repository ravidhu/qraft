# Migrating from dbt to Qraft

This guide is for experienced dbt users evaluating or switching to Qraft. It covers every major concept in dbt and shows the Qraft equivalent (or notes where one does not exist). Code examples are side-by-side where possible.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Templating](#templating)
- [Macros](#macros)
- [Model Configuration](#model-configuration)
- [Materializations](#materializations)
- [Testing](#testing)
- [Sources](#sources)
- [Variables](#variables)
- [Packages](#packages)
- [Environments](#environments)
- [Model Selection](#model-selection)
- [Features dbt Has That Qraft Does Not](#features-dbt-has-that-qraft-does-not)

---

## Project Structure

dbt splits configuration across two files: `dbt_project.yml` (project-level settings) and `profiles.yml` (connection credentials, typically in `~/.dbt/`). Qraft consolidates everything into a single `project.yaml` at the project root.

**dbt**

```
my_project/
  dbt_project.yml
  profiles.yml          # or ~/.dbt/profiles.yml
  models/
    staging/
      stg_orders.sql
    marts/
      fct_orders.sql
  macros/
    my_macro.sql
  tests/
    assert_positive.sql
  seeds/
    countries.csv
```

**Qraft**

```
my_project/
  project.yaml          # single config file
  models/
    staging/
      stg_orders.sql
    marts/
      fct_orders.sql
  macros/
    my_macros.py         # Python, not Jinja
```

**dbt — dbt_project.yml + profiles.yml**

```yaml
# dbt_project.yml
name: my_project
version: '1.0.0'
profile: my_project
model-paths: ["models"]
macro-paths: ["macros"]

# profiles.yml
my_project:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: dev.duckdb
    prod:
      type: postgres
      host: db.example.com
      user: "{{ env_var('DB_USER') }}"
      password: "{{ env_var('DB_PASS') }}"
      dbname: analytics
      schema: public
```

**Qraft — project.yaml**

```yaml
name: my_project

connection:
  type: duckdb
  path: dev.duckdb

schema: public
materialization: view

sources: {}
vars: {}

environments:
  local:
  prod:
    connection:
      type: postgres
      host: db.example.com
      user: ${DB_USER}
      password: ${DB_PASS}
      database: analytics
    schema: public
```

Key differences:

- No separate profiles file. Connection details live in `project.yaml`.
- Environment variables use `${VAR}` syntax (via python-dotenv), not Jinja `env_var()`.
- The default (top-level) configuration acts as your dev environment.

---

## Templating

dbt uses full Jinja2 templating. Qraft uses a lightweight regex-based system that supports `ref()`, `source()`, and `{{ variable }}` substitution — but nothing else from Jinja.

**dbt**

```sql
SELECT
  {{ dbt_utils.star(ref('stg_orders')) }},
  {{ var('tax_rate') }} AS tax_rate,
  {% if target.name == 'prod' %}
    created_at AT TIME ZONE 'UTC'
  {% else %}
    created_at
  {% endif %}
FROM {{ ref('stg_orders') }}
WHERE status IN ({{ var('valid_statuses') | join(', ') }})
```

**Qraft**

```sql
SELECT
  *,
  {{ tax_rate }} AS tax_rate,
  created_at
FROM ref('stg_orders')
WHERE status IN ('active', 'pending')
```

What carries over:

- `ref('model_name')` — same syntax, quotes required.
- `source('source_name', 'table_name')` — same syntax, quotes required.
- `{{ var_name }}` for variable substitution (no `var()` function wrapper needed).

What does not carry over:

- No Jinja control flow (`{% if %}`, `{% for %}`, `{% set %}`).
- No Jinja filters (`| join`, `| upper`, etc.).
- No `dbt_utils` or any Jinja-based utility package.
- No `target` context variable.

If your dbt project relies heavily on Jinja logic, you will need to either simplify the SQL or move the logic into Python macros.

---

## Macros

dbt macros are Jinja templates. Qraft macros are plain Python functions that return SQL strings.

**dbt — macros/cents_to_dollars.sql**

```sql
{% macro cents_to_dollars(column_name) %}
  ({{ column_name }} / 100.0)::NUMERIC(16,2)
{% endmacro %}
```

Usage in a model:

```sql
SELECT
  order_id,
  {{ cents_to_dollars('amount') }} AS amount_dollars
FROM {{ ref('stg_orders') }}
```

**Qraft — macros/utils.py**

```python
def cents_to_dollars(column_name: str) -> str:
    return f"({column_name} / 100.0)::NUMERIC(16,2)"
```

Usage in a model (note the front-matter declaring the macro module):

```sql
---
macros: [utils]
---
SELECT
  order_id,
  cents_to_dollars(amount) AS amount_dollars
FROM ref('stg_orders')
```

Key differences:

- Macros are Python files in the `macros/` directory, not Jinja `.sql` files.
- Each model must declare which macro modules it uses via `macros: [module_name]` in YAML front-matter.
- Macro functions receive arguments and return SQL strings. You have access to the full Python standard library.
- No implicit `this`, `target`, or `adapter` context is passed to macros.

---

## Model Configuration

dbt uses `config()` blocks inside Jinja or `schema.yml` properties. Qraft uses YAML front-matter delimited by `---` at the top of each SQL file.

**dbt**

```sql
{{
  config(
    materialized='table',
    tags=['daily', 'finance'],
    schema='marts'
  )
}}

SELECT * FROM {{ ref('stg_orders') }}
```

Or in `schema.yml`:

```yaml
models:
  - name: fct_orders
    config:
      materialized: table
      tags: ['daily', 'finance']
```

**Qraft**

```sql
---
materialization: table
tags: [daily, finance]
schema: marts
---

SELECT * FROM ref('stg_orders')
```

The front-matter block must be the very first thing in the file. All configuration for a model lives here — there is no equivalent to dbt's `schema.yml` property files for model-level config.

---

## Materializations

Both tools support `view`, `table`, `ephemeral`, and `incremental`. Qraft adds `materialized_view` as a first-class materialization. Incremental models work differently.

### Standard materializations

| dbt | Qraft | Notes |
|-----|-------|-------|
| `view` | `view` | Same behavior |
| `table` | `table` | Same behavior |
| `ephemeral` | `ephemeral` | Same — inlined as CTE |
| `incremental` | `table_incremental` | Different mechanism (see below) |
| — | `materialized_view` | Not available in dbt core |

### Incremental models

**dbt**

```sql
{{
  config(
    materialized='incremental',
    unique_key='order_id'
  )
}}

SELECT *
FROM {{ ref('stg_orders') }}
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

**Qraft**

```sql
---
materialization: table_incremental
unique_key: order_id
---

SELECT *
FROM ref('stg_orders')
WHERE updated_at >= CURRENT_DATE - INTERVAL '3 days'
```

Key differences:

- The materialization is called `table_incremental`, not `incremental`.
- There is no `is_incremental()` function or `{{ this }}` variable. Qraft automatically detects whether the target table already exists. If the table does not exist, Qraft runs a full `CREATE TABLE AS`. If it does exist, Qraft runs `DELETE` + `INSERT` using the `unique_key` for upsert.
- Your SQL should always select the rows you want to insert — Qraft handles the create-vs-upsert logic at runtime.
- No merge strategies to configure — Qraft uses delete+insert on the unique key.

---

## Testing

dbt defines tests in `schema.yml` files using built-in or custom test types. Qraft defines tests directly in the model's SQL front-matter under a `columns:` block.

**dbt — models/schema.yml**

```yaml
models:
  - name: fct_orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: status
        tests:
          - accepted_values:
              values: ['active', 'completed', 'cancelled']
      - name: customer_id
        tests:
          - relationships:
              to: ref('dim_customers')
              field: customer_id
```

**Qraft — models/fct_orders.sql**

```sql
---
materialization: table
columns:
  - name: order_id
    tests: [unique, not_null]
  - name: status
    tests:
      - accepted_values:
          values: ['active', 'completed', 'cancelled']
  - name: customer_id
    tests:
      - relationships:
          to: ref('dim_customers')
          field: customer_id
---

SELECT * FROM ref('stg_orders')
```

Qraft ships with 7 built-in test types. The tests are co-located with the model definition rather than in a separate YAML file.

---

## Sources

dbt declares sources in a `sources.yml` file and references them with `{{ source('name', 'table') }}`. Qraft declares sources in `project.yaml` and references them with `source('name', 'table')`.

**dbt — models/sources.yml**

```yaml
sources:
  - name: raw
    database: raw_db
    schema: public
    tables:
      - name: orders
      - name: customers
```

Usage:

```sql
SELECT * FROM {{ source('raw', 'orders') }}
```

**Qraft — project.yaml**

```yaml
sources:
  raw:
    database: raw_db
    schema: public
    tables:
      - orders
      - customers
```

Usage:

```sql
SELECT * FROM source('raw', 'orders')
```

The syntax is the same — `source('name', 'table')` with quotes. The difference is there is no Jinja `{{ }}` wrapper.

---

## Variables

dbt variables are defined in `dbt_project.yml` and accessed with `{{ var('name') }}`. They can be overridden from the CLI with `--vars`. Qraft variables are defined in `project.yaml` and accessed with `{{ name }}`.

**dbt**

```yaml
# dbt_project.yml
vars:
  tax_rate: 0.08
  start_date: '2023-01-01'
```

```sql
SELECT *, {{ var('tax_rate') }} AS tax_rate
FROM {{ ref('stg_orders') }}
WHERE created_at >= '{{ var("start_date") }}'
```

CLI override: `dbt run --vars '{tax_rate: 0.10}'`

**Qraft**

```yaml
# project.yaml
vars:
  tax_rate: "0.08"
  start_date: "2023-01-01"
```

```sql
SELECT *, {{ tax_rate }} AS tax_rate
FROM ref('stg_orders')
WHERE created_at >= '{{ start_date }}'
```

Key differences:

- Variables are string-only in Qraft. They are inserted via simple text substitution.
- There is no CLI override for variables. Values come from `project.yaml` only.
- The syntax is `{{ var_name }}` directly, not `{{ var('var_name') }}`.

---

## Packages

dbt has a package ecosystem (dbt Hub) managed via `packages.yml`. Qraft uses standard Python packages installed with pip (or uv).

**dbt — packages.yml**

```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: "1.1.0"
  - package: calogica/dbt_expectations
    version: "0.9.0"
```

```bash
dbt deps
```

**Qraft**

```bash
uv add qraft-utils
# or: pip install qraft-utils
```

Then use in macros or reference as needed. The `qraft-utils` package provides reusable macro functions. The ecosystem is much smaller than dbt's — there is no equivalent to `dbt_utils`, `dbt_expectations`, or the broader dbt package registry.

---

## Environments

dbt uses `profiles.yml` with named targets. Qraft uses an `environments:` block in `project.yaml`.

**dbt — profiles.yml**

```yaml
my_project:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: dev.duckdb
    staging:
      type: postgres
      host: staging.example.com
      dbname: analytics
      schema: staging
    prod:
      type: postgres
      host: prod.example.com
      dbname: analytics
      schema: public
```

```bash
dbt run --target prod
```

**Qraft — project.yaml**

```yaml
name: my_project

connection:
  type: duckdb
  path: dev.duckdb

schema: public
materialization: view

environments:
  local:
  staging:
    connection:
      type: postgres
      host: staging.example.com
      database: analytics
    schema: staging
  prod:
    connection:
      type: postgres
      host: prod.example.com
      database: analytics
    schema: public
```

```bash
qraft run --env prod
```

The top-level config acts as the default environment. Named environments override those defaults.

---

## Model Selection

Both tools support graph-aware selection syntax. Qraft covers the most common patterns but does not support everything dbt offers.

| Pattern | dbt | Qraft |
|---------|-----|-------|
| Single model | `dbt run -s my_model` | `qraft run -s my_model` |
| Model + downstream | `dbt run -s my_model+` | `qraft run -s my_model+` |
| Upstream + model | `dbt run -s +my_model` | `qraft run -s +my_model` |
| Tag selection | `dbt run -s tag:daily` | `qraft run -s tag:daily` |
| Prefix wildcard | Not built-in | `qraft run -s stg_*` |
| Multiple patterns | `dbt run -s model_a model_b` | Not supported |
| State comparison | `dbt run -s state:modified` | Not supported |
| Named selectors | `dbt run --selector my_selector` | Not supported |
| Path selection | `dbt run -s path:models/staging` | Not supported |
| Method chaining | `dbt run -s +tag:daily,1+` | Not supported |

Qraft's `prefix*` wildcard is useful for selecting groups of models that share a naming convention (e.g., `stg_*` for all staging models).

---

## Features dbt Has That Qraft Does Not

The following dbt features have no equivalent in Qraft. If your project depends on any of these, you will need to find workarounds or accept the gap.

| dbt Feature | Description | Workaround in Qraft |
|-------------|-------------|---------------------|
| **Snapshots** | Type-2 slowly changing dimension tracking | Implement manually in SQL or use database-native CDC |
| **Seeds** | Load CSV files as tables | Load CSVs using your database's native import tools |
| **Hooks** (pre/post) | Run SQL before or after models | Handle in external orchestration (e.g., Airflow, cron) |
| **Exposures** | Document downstream consumers | Document manually |
| **run_query()** | Execute SQL during compilation | Move logic to Python macros or pre-processing scripts |
| **Adapter dispatch** | Cross-database SQL generation | Write database-specific SQL or use Python macros |
| **Jinja control flow** | `{% if %}`, `{% for %}`, `{% set %}` | Use Python macros to generate dynamic SQL |
| **Model contracts** | Enforce column types and constraints | Use database-level constraints or tests |
| **Freshness checks** | Source freshness monitoring | Implement with external monitoring |
| **Documentation site** | Auto-generated docs with `dbt docs` | Use `qraft docs` for lineage catalog |
| **Defer/state** | Compare against production artifacts | Not available |

---

## Migration Checklist

A practical order of operations for migrating a dbt project:

1. **Create `project.yaml`** — Translate `dbt_project.yml` and `profiles.yml` into a single file. Use `connection:` with `type:` for the engine.
2. **Move models** — Copy SQL files to the Qraft `models/` directory.
3. **Replace `ref()` syntax** — Change `{{ ref('model') }}` to `ref('model')` (remove the Jinja `{{ }}` wrapper, keep the quotes).
4. **Replace `source()` syntax** — Change `{{ source('src', 'tbl') }}` to `source('src', 'tbl')` (remove Jinja wrapper, keep quotes). Declare sources in `project.yaml`.
5. **Replace `config()` blocks** — Convert to YAML front-matter between `---` delimiters. Use `materialization:` (not `materialized:`).
6. **Convert variables** — Change `{{ var('name') }}` to `{{ name }}` and move variable definitions to `project.yaml`. All values must be strings.
7. **Strip Jinja logic** — Remove or rewrite any `{% if %}`, `{% for %}`, or `{% set %}` blocks. Move complex logic to Python macros.
8. **Convert macros** — Rewrite Jinja macros as Python functions in the `macros/` directory. Add `macros: [module]` to front-matter of models that use them.
9. **Convert tests** — Move test definitions from `schema.yml` into each model's YAML front-matter under `columns:`.
10. **Handle incremental models** — Change materialization to `table_incremental`, set `unique_key`, remove `is_incremental()` guards and `{{ this }}` references. Qraft auto-detects table existence.
11. **Validate** — Run `qraft validate --env local` and check that all references resolve correctly.
12. **Run and compare** — Execute with `qraft run --env local` and validate outputs against your dbt results.
