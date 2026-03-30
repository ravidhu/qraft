# Configuration Reference

All project configuration lives in a single `project.yaml` file at the root of your project.

## Full Schema

```yaml
name: my_project            # Project name (required)
version: "0.1.0"            # Optional version string

connection:                  # Database connection (required)
  type: duckdb              # Engine type: "duckdb"
  path: dev.duckdb          # Engine-specific parameters
  # Other params depend on the engine type

schema: analytics           # Default schema for all models (default: public)
materialization: view       # Default: view, table, ephemeral, materialized_view, table_incremental

sources:                     # External data sources (optional)
  source_name:
    schema: raw_data        # Schema where source tables live
    database: my_db         # Optional: database name (for 3-part names)
    tables:                 # List of table names
      - customers
      - orders

vars:                        # Variables available in SQL templates (optional)
  min_amount: "0"
  trial_days: "14"

environments:                # Per-environment overrides (optional)
  local:                    # Empty = inherits all defaults
  staging:
    schema: analytics_staging
  prod:
    schema: analytics_prod
    connection:
      type: postgres
      host: prod-db.example.com
      user: ${PROD_USER}
      password: ${PROD_PASSWORD}
    vars:
      min_amount: "100"
```

## Fields

### `name`

**Required.** The project name. Used for display purposes.

### `connection`

**Required.** Database connection settings. The `type` field determines which engine is used.

#### DuckDB

```yaml
connection:
  type: duckdb
  path: dev.duckdb         # Path to the DuckDB file (use :memory: for in-memory)
  init_sql: "INSTALL postgres; LOAD postgres"  # Optional: SQL to run after connecting
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `path` | no | `:memory:` | Path to the DuckDB database file |
| `init_sql` | no | — | SQL statements to execute after connecting (semicolon-separated) |

The `init_sql` parameter is useful for loading DuckDB extensions or attaching external databases. For example, to read from a PostgreSQL source using DuckDB's `postgres` extension:

```yaml
connection:
  type: duckdb
  path: analytics.duckdb
  init_sql: "INSTALL postgres; LOAD postgres; ATTACH 'postgresql://user:pass@host:5432/db' AS pg (TYPE POSTGRES, READ_ONLY)"
```

See the [postgres_to_duckdb example](../examples/postgres_to_duckdb/) for a complete working setup.

#### PostgreSQL

Requires `uv add qraft[postgres]`.

```yaml
connection:
  type: postgres
  host: localhost
  port: 5432
  user: ${DB_USER}
  password: ${DB_PASSWORD}
  database: analytics
  sslmode: require            # Optional: SSL mode
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `host` | no | `localhost` | Database hostname |
| `port` | no | `5432` | Database port |
| `user` | no | `postgres` | Username |
| `password` | no | — | Password |
| `database` | no | `postgres` | Database name |
| `sslmode` | no | — | SSL mode (`require`, `verify-ca`, `verify-full`, etc.) |

#### MySQL / MariaDB

Requires `uv add qraft[mysql]`.

```yaml
connection:
  type: mysql
  host: localhost
  port: 3306
  user: ${DB_USER}
  password: ${DB_PASSWORD}
  database: analytics
  charset: utf8mb4            # Optional: character set
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `host` | no | `localhost` | Database hostname |
| `port` | no | `3306` | Database port |
| `user` | no | `root` | Username |
| `password` | no | — | Password |
| `database` | yes | — | Database name |
| `charset` | no | — | Character set (e.g., `utf8mb4`) |
| `ssl` | no | — | SSL configuration dict |

#### Trino

Requires `uv add qraft[trino]`.

```yaml
connection:
  type: trino
  host: localhost
  port: 8080
  user: ${TRINO_USER}
  catalog: iceberg
  schema: default             # Optional: default schema
  http_scheme: https          # Optional: use HTTPS (default: http)
  roles:                      # Optional: catalog roles
    iceberg: admin
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `host` | no | `localhost` | Trino coordinator hostname |
| `port` | no | `8080` | Trino coordinator port |
| `user` | no | `trino` | Username for authentication |
| `catalog` | yes | — | Default catalog for queries |
| `schema` | no | — | Default schema for queries |
| `http_scheme` | no | `http` | Use `https` for TLS connections |
| `roles` | no | — | Dict of catalog-to-role mappings for authorization |

#### Tested Versions

The following versions are used in the [example projects](../examples/) and are the versions Qraft is regularly tested against. Server versions come from the Docker images in each example's `docker-compose.yml`; driver versions are locked in `uv.lock`.

| Engine | Python Driver | Driver Version | Server Version |
|--------|--------------|----------------|----------------|
| DuckDB | `duckdb` | 1.5.0 | (embedded) |
| PostgreSQL | `psycopg` | 3.3.3 | PostgreSQL 17 |
| MySQL/MariaDB | `pymysql` | 1.1.2 | MariaDB 11.7 |
| Trino | `trino` | 0.337.0 | Trino 480 |

Minimum driver requirements: duckdb >= 1.0, psycopg >= 3.1, pymysql >= 1.1, trino >= 0.328.

### `schema`

**Optional.** Default: `public`. The default schema where models are materialized. A model named `stg_orders` in schema `analytics` becomes `analytics.stg_orders`.

### `materialization`

Default materialization strategy for all models. Can be overridden per model with front-matter.

- `view` (default) — `CREATE OR REPLACE VIEW`
- `table` — `DROP TABLE IF EXISTS; CREATE TABLE AS`
- `table_incremental` — `INSERT INTO` (append), or `DELETE + INSERT` with `unique_key` (upsert). On first run, the table is created automatically.
- `ephemeral` — No database object created; inlined as a CTE into downstream models
- `materialized_view` — `CREATE MATERIALIZED VIEW IF NOT EXISTS` (Postgres, Trino only)

Not all engines support all materializations. See [Materialization Types — Engine Support Matrix](materialization_types.md#engine-support-matrix) for the full compatibility table.

### `sources`

Dictionary of named data sources. Each source maps to external tables your models read from. Sources are **read-only references** — at compile time, `source()` calls resolve to fully qualified table names that the primary engine must be able to query. Qraft does not open separate database connections for sources. See [Concepts — Cross-Database Access](concepts.md#cross-database-access) for details on how to read from external databases.

```yaml
sources:
  crm:
    schema: crm_raw
    tables:
      - accounts
      - contacts
  billing:
    database: billing_db     # Optional 3-part name
    schema: billing_raw
    tables:
      - invoices
      - payments
```

In SQL: `source('crm', 'accounts')` resolves to `crm_raw.accounts`.
With a database: `source('billing', 'invoices')` resolves to `billing_db.billing_raw.invoices`.

### `vars`

Dictionary of string key-value pairs. Available in SQL as `{{ key }}`.

```yaml
vars:
  min_order_amount: "0"
  currency: "USD"
```

All values must be strings (wrap numbers in quotes). Variables can reference other variables (chaining) — the resolver runs multiple passes until all references are resolved. The maximum number of passes defaults to 10 and can be configured via the `QRAFT_MAX_VAR_PASSES` environment variable.

### `environments`

Dictionary of named environments. Each environment can override any top-level field. Overrides are deep-merged with the base configuration.

```yaml
environments:
  local:                   # Empty = use base config as-is
  prod:
    schema: analytics_prod # Override schema
    connection:            # Override connection
      type: postgres
      host: prod.example.com
    vars:                  # Override specific vars
      min_order_amount: "100"
```

## Environment Resolution

```mermaid
flowchart TD
    A["project.yaml"] --> B["Parse YAML"]
    B --> C["Resolve ${ENV_VAR} placeholders"]
    C --> D["Validate config structure"]
    D --> E{"--env flag"}
    E --> F["Load base config<br/><small>connection, schema, materialization, sources, vars</small>"]
    F --> G["Deep-merge environment overrides"]

    G --> H["connection:<br/>type change → replace<br/>same type → merge params"]
    G --> I["sources:<br/>per-source field merge"]
    G --> J["vars:<br/>key-level merge"]
    G --> K["schema, materialization:<br/>direct override"]

    H --> L["EnvConfig"]
    I --> L
    J --> L
    K --> L
```

When you run `qraft run --env prod`, the configuration is resolved as follows:

1. Start with the base config (all top-level fields)
2. Deep-merge the `prod` environment overrides on top
3. For `vars` and `sources`, individual keys are merged (not replaced entirely)
4. For `connection`, if the engine type changes the override replaces the base connection entirely; if the type stays the same, individual parameters are merged

### Merge Example

Base:
```yaml
schema: analytics
vars:
  min_amount: "0"
  currency: "USD"
```

Environment override:
```yaml
schema: analytics_prod
vars:
  min_amount: "100"
```

Result:
```yaml
schema: analytics_prod       # Overridden
vars:
  min_amount: "100"          # Overridden
  currency: "USD"            # Inherited from base
```

## Environment Variables

Use `${ENV_VAR}` syntax in `project.yaml` to reference shell environment variables. This is useful for secrets that shouldn't be committed to version control.

```yaml
connection:
  type: postgres
  host: ${DB_HOST}
  user: ${DB_USER}
  password: ${DB_PASSWORD}
```

Qraft loads `.env` files automatically via `python-dotenv`. Create a `.env` file in your project root:

```
DB_HOST=localhost
DB_USER=analytics
DB_PASSWORD=secret
```

Add `.env` to your `.gitignore` to keep secrets out of version control.

## Model Front-matter

Models support YAML front-matter between `---` delimiters to override settings and define tests. See [Concepts — Front-matter](concepts.md#front-matter) for usage.

### `columns`

The `columns` block defines column-level metadata and data tests:

```sql
---
materialization: table
columns:
  - name: order_id
    description: Unique order identifier
    tests:
      - not_null
      - unique
  - name: status
    description: Current order status
    tests:
      - accepted_values:
          values: [pending, shipped, delivered, cancelled]
  - name: customer_id
    tests:
      - not_null
      - relationships:
          to: ref('stg_customers')
          field: customer_id
  - name: amount
    tests:
      - accepted_range:
          min_value: 0
---
SELECT ...
```

Each column entry supports:

| Field | Description |
|-------|-------------|
| `name` | Column name (required) |
| `description` | Human-readable column description (included in manifest) |
| `tests` | List of data tests to run on this column |

### Available Tests

| Test | Parameters | Description |
|------|-----------|-------------|
| `not_null` | -- | Column has no NULL values |
| `unique` | -- | Column has no duplicate values |
| `accepted_values` | `values` (list) | Column only contains values from the list |
| `relationships` | `to`, `field` | Every value exists in the referenced model's column |
| `number_of_rows` | `min_value` (or `min`; default: `1`) | Table has at least the specified number of rows |
| `accepted_range` | `min_value`/`max_value` (or `min`/`max`; at least one) | Column values fall within the numeric range |
| `unique_combination_of_columns` | `combination` or `columns` (list of column names) | No duplicate rows for the given column combination |

### Test Configuration

Each test supports optional configuration:

```yaml
columns:
  - name: email
    tests:
      - not_null:
          severity: warn       # "error" (default) or "warn"
          where: "active = true"  # Filter rows before testing
```

- **`severity: warn`** -- Test failures are reported but don't cause a non-zero exit code
- **`where`** -- SQL WHERE clause applied to the test results (the test query is wrapped in a subquery and this clause filters the output)
