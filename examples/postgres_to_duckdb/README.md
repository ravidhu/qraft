# Postgres to DuckDB

A lightweight example showing how to read from a live PostgreSQL database and write analytics tables into a local DuckDB file. Uses DuckDB's `postgres` extension to attach PostgreSQL as a foreign data source -- no Trino required.

## How It Works

DuckDB's `postgres` extension lets you `ATTACH` a PostgreSQL database and query it directly. Source tables are read from PostgreSQL, while Qraft models are materialized into local DuckDB tables/views.

```mermaid
graph LR
    subgraph PostgreSQL
        A[app_public.users]
        B[app_public.orders]
        C[app_public.products]
    end

    EXT{{DuckDB postgres extension}}

    subgraph DuckDB - analytics.duckdb
        subgraph Staging
            SA[stg_users]
            SB[stg_orders]
            SC[stg_products]
        end

        subgraph Marts
            F1[fct_user_orders]
            F2[fct_product_performance]
        end
    end

    A -- source --> EXT
    B -- source --> EXT
    C -- source --> EXT

    EXT -- read/write --> SA
    EXT -- read/write --> SB
    EXT -- read/write --> SC

    SA --> F1
    SB --> F1

    SC --> F2
    SB --> F2
```

## Data Model

| Layer   | Models                                      | Description              |
|---------|---------------------------------------------|--------------------------|
| staging | `stg_users`, `stg_orders`, `stg_products`   | Clean and rename         |
| marts   | `fct_user_orders`, `fct_product_performance` | Materialized as tables   |

## Quick Start

```bash
cd examples/postgres_to_duckdb

# 1. Start PostgreSQL with seed data
docker compose up -d

# 2. Wait for PostgreSQL to be ready
docker compose exec postgres pg_isready -U qraft -d source

# 3. Validate the project
qraft validate --env local

# 4. View the dependency graph
qraft dag

# 5. Compile SQL (preview)
qraft compile --env local

# 6. Run all models (reads from Postgres, writes to analytics.duckdb)
qraft run --env local
```

## Connection Configuration

The key is the `init_sql` parameter in `project.yaml`, which attaches PostgreSQL on DuckDB startup:

```yaml
connection:
  type: duckdb
  path: analytics.duckdb
  init_sql: >-
    INSTALL postgres;
    LOAD postgres;
    ATTACH 'postgresql://qraft:qraft@localhost:5432/source'
    AS pg (TYPE POSTGRES, READ_ONLY)
```

Sources reference the attached database:

```yaml
sources:
  app:
    database: pg           # ← the ATTACH alias
    schema: app_public
    tables: [users, orders, products]
```

This resolves `source('app', 'users')` to `pg.app_public.users`, which DuckDB reads directly from PostgreSQL.

## Project Variables

| Variable      | Default | Description                           |
|---------------|---------|---------------------------------------|
| `active_days` | `90`    | Days threshold for active user status |
