# Materialization Types

Qraft supports five materialization types that control how a model's SQL is turned into a database object. Each type generates different DDL, trades off between storage cost and query performance, and fits specific use cases.

## Setting the Materialization

**Project-wide default** in `project.yaml`:

```yaml
materialization: view
```

**Per-model override** via front-matter in the SQL file:

```sql
---
materialization: table
---
SELECT ...
```

The per-model front-matter always takes precedence over the project default.

---

## `view` (default)

Creates or replaces a SQL view. No data is stored -- the query executes on every read.

### Generated DDL

```sql
CREATE OR REPLACE VIEW schema.model_name AS
SELECT ...
```

### When to use

- **Lightweight transformations** -- renaming columns, casting types, simple filters
- **Staging models** that clean raw data before downstream aggregation
- **Any model where freshness matters more than speed** -- views always return the latest data from their source tables
- **Development and prototyping** -- fast iteration since no data needs to be rebuilt

### Trade-offs

| Pros | Cons |
|------|------|
| No storage cost | Query runs every time the view is read |
| Always returns fresh data | Expensive aggregations re-execute on each read |
| Instant "build" -- only DDL to execute | Downstream consumers may experience slow reads |

### Example

```sql
-- models/bronze/stg_customers.sql
SELECT
    id        AS customer_id,
    name      AS customer_name,
    email,
    created_at
FROM source('raw', 'customers')
```

---

## `table`

Drops and recreates a table on every run. Stores the full result set in the database.

### Generated DDL

```sql
DROP TABLE IF EXISTS schema.model_name;
CREATE TABLE schema.model_name AS
SELECT ...
```

### When to use

- **Expensive aggregations or joins** that would be too slow to recompute on every read
- **Gold-layer reporting tables** queried frequently by dashboards or BI tools
- **Intermediate models** where downstream models ref the same data repeatedly
- **Any model where read performance matters more than build time**

### Trade-offs

| Pros | Cons |
|------|------|
| Fast reads -- data is pre-computed | Full rebuild on every run |
| No repeated computation for downstream consumers | Uses storage space |
| Predictable query performance | Data is only as fresh as the last build |

### Example

```sql
---
materialization: table
---
SELECT
    c.customer_id,
    c.customer_name,
    COUNT(o.order_id)       AS total_orders,
    SUM(o.order_total)      AS lifetime_spend
FROM ref('stg_customers') c
LEFT JOIN ref('stg_orders') o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
```

---

## `ephemeral`

No database object is created. The model's SQL is injected as a CTE (Common Table Expression) into every downstream model that `ref()`s it.

### Generated DDL

None -- ephemeral models produce no DDL.

### How it works

When a downstream model references an ephemeral, Qraft prepends a `WITH` clause containing the ephemeral's compiled SQL:

```sql
-- The ephemeral model (int_revenue.sql)
---
materialization: ephemeral
---
SELECT account_id, SUM(amount) AS total
FROM ref('stg_invoices')
GROUP BY account_id
```

```sql
-- A downstream model that refs it
SELECT * FROM ref('int_revenue') WHERE total > 1000
```

Compiles to:

```sql
WITH int_revenue AS (
  SELECT account_id, SUM(amount) AS total
  FROM analytics.stg_invoices
  GROUP BY account_id
)
SELECT * FROM int_revenue WHERE total > 1000
```

Key behaviors:

- **Transitive injection** -- if ephemeral A refs ephemeral B, both CTEs are injected into any downstream model that refs A
- **Deduplication** -- if a model refs two ephemerals that both ref the same third ephemeral, the shared CTE appears only once
- **Merging** -- if the downstream model already has its own `WITH` clause, the ephemeral CTEs are prepended and the downstream's CTEs are appended with commas

### When to use

- **Reusable SQL logic** that multiple models share but that doesn't warrant its own table or view
- **Intermediate aggregations** that are only consumed by one or two downstream models
- **Keeping your database clean** -- no extra objects cluttering the schema
- **DRY principle** -- define logic once, inject everywhere

### Trade-offs

| Pros | Cons |
|------|------|
| No database object -- zero storage, zero clutter | SQL is duplicated into every consumer (can bloat compiled queries) |
| Always fresh -- recomputed inline | Cannot be queried directly for debugging |
| Great for shared logic | Performance impact if the CTE is expensive and referenced by many models |

### Example

```sql
---
materialization: ephemeral
description: Sales pipeline aggregation per account (injected as CTE)
tags: [silver, crm]
---
SELECT
    o.account_id,
    COUNT(DISTINCT o.opportunity_id)   AS total_opportunities,
    SUM(CASE WHEN o.stage = 'closed_won' THEN o.deal_amount ELSE 0 END)
                                        AS closed_won_amount,
    SUM(CASE WHEN o.stage NOT IN ('closed_won','closed_lost') THEN o.deal_amount ELSE 0 END)
                                        AS pipeline_amount
FROM ref('stg_opportunities') o
GROUP BY o.account_id
```

---

## `table_incremental`

Appends or upserts new rows instead of rebuilding the entire table. On the first run it creates the table; on subsequent runs it inserts only new data.

### Generated DDL

**First run** (table does not exist):

```sql
CREATE TABLE schema.model_name AS
SELECT ...
```

**Subsequent runs without `unique_key`** (append-only):

```sql
INSERT INTO schema.model_name
SELECT ...
```

**Subsequent runs with `unique_key`** (upsert):

```sql
DELETE FROM schema.model_name
WHERE account_id IN (SELECT account_id FROM (SELECT ...));
INSERT INTO schema.model_name
SELECT ...
```

### How it works

The runtime automatically detects whether the target table exists:

- If the table **does not exist**, Qraft runs `CREATE TABLE ... AS SELECT ...` to create it with the full dataset
- If the table **exists**, Qraft runs the insert or upsert DDL

No template syntax or conditional blocks are needed -- the behavior is fully automatic.

### Configuration

| Front-matter field | Required | Description |
|--------------------|----------|-------------|
| `materialization: table_incremental` | Yes | Enables incremental behavior |
| `unique_key` | No | Column used for upsert deduplication. Without it, rows are appended (no dedup) |

### When to use

- **Large, append-heavy datasets** -- event logs, clickstream data, transaction history
- **Tables where a full rebuild is too expensive** or takes too long
- **Fact tables** that grow over time and where only new records need processing
- **Any model with a reliable timestamp or incrementing key** that can filter "what's new"

### Trade-offs

| Pros | Cons |
|------|------|
| Much faster builds -- only processes new data | More complex logic (must define what "new" means) |
| Efficient for large datasets | Risk of data drift if the incremental filter misses rows |
| Supports upsert via `unique_key` | First run is still a full build |

### Example

```sql
---
materialization: table_incremental
unique_key: account_id
macros: [saas_utils]
description: Unified account health scorecard
tags: [gold, critical]
---
SELECT
    ae.account_id,
    ae.account_name,
    ae.mrr,
    ae.subscription_status,
    coalesce_zero(rev.total_paid)    AS lifetime_revenue,
    coalesce_zero(sp.pipeline_amount) AS open_pipeline,
    coalesce_zero(pe.active_users)   AS active_users,
    health_score(ae.subscription_status, pe.active_users, pe.total_events, ae.mrr)
                                      AS health_status
FROM ref('int_accounts_enriched') ae
LEFT JOIN ref('int_revenue_by_account') rev ON ae.account_id = rev.account_id
LEFT JOIN ref('int_sales_pipeline') sp      ON ae.account_id = sp.account_id
LEFT JOIN ref('int_product_engagement') pe  ON ae.account_id = pe.account_id
```

---

## `materialized_view`

Creates a database-managed materialized view. The database stores the query result and can refresh it on its own schedule.

### Generated DDL

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS schema.model_name AS
SELECT ...
```

### When to use

- **Database-native refresh is preferred** -- let the database handle when and how to refresh the cached data
- **PostgreSQL, Redshift, or other databases with native materialized view support**
- **Dashboards or reports** that need fast reads but can tolerate slightly stale data
- **When you want cached query results** without managing table_incremental logic yourself

### Trade-offs

| Pros | Cons |
|------|------|
| Database manages caching and refresh | Not all databases support materialized views |
| Fast reads from cached data | Refresh strategy depends on the database engine |
| Simpler than table_incremental -- no filter logic needed | Uses `IF NOT EXISTS` -- won't update the definition on re-run |
| Native database feature | Less control over refresh timing compared to table rebuilds |

### Example

```sql
---
materialization: materialized_view
---
SELECT
    product_id,
    COUNT(*)           AS total_sales,
    SUM(sale_amount)   AS total_revenue,
    AVG(sale_amount)   AS avg_sale_value
FROM ref('stg_sales')
GROUP BY product_id
```

---

## Quick Reference

| Type | Database Object | Data Stored | Rebuild Behavior | Best For |
|------|----------------|-------------|------------------|----------|
| `view` | VIEW | No | Virtual (runs on read) | Staging, lightweight transforms |
| `table` | TABLE | Yes | Full drop + recreate | Expensive aggregations, reports |
| `ephemeral` | None (CTE) | No | Injected inline | Reusable logic, DRY SQL |
| `table_incremental` | TABLE | Yes | Append or upsert | Large append-heavy datasets |
| `materialized_view` | MATERIALIZED VIEW | Yes | Database-managed | DB-native caching |

## Engine Support Matrix

Not all engines support all materialization types. Using an unsupported materialization raises an error at compile time.

| Materialization | DuckDB | PostgreSQL | MySQL/MariaDB | Trino |
|----------------|--------|------------|---------------|-------|
| `view` | Yes | Yes | Yes | Yes |
| `table` | Yes | Yes | Yes | Yes |
| `ephemeral` | Yes | Yes | Yes | Yes |
| `table_incremental` | Yes | Yes | Yes | Yes |
| `materialized_view` | No | Yes | No | Yes |

> **Note:** DuckDB and MySQL do not support `materialized_view`. If you need cached query results on these engines, use `table` instead and rebuild on your own schedule.

## Choosing a Materialization

```
Is the model just renaming/casting columns?
  └─ Yes → view

Is the query expensive and read frequently?
  └─ Yes → Is the dataset append-heavy with a reliable timestamp?
              └─ Yes → table_incremental
              └─ No  → table

Is the logic reused by multiple models but doesn't need its own object?
  └─ Yes → ephemeral

Does your database support materialized views and you want DB-managed refresh?
  └─ Yes → materialized_view (PostgreSQL/Trino only)
```
