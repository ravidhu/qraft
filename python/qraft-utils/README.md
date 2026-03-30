# qraft-utils

Standard macro library for [Qraft](https://github.com/ravidhu/qraft) SQL projects.

Provides reusable SQL macros that work across DuckDB, PostgreSQL, MySQL, and Trino. Macros are plain Python functions that generate SQL strings — they are expanded at compile time by Qraft's macro system.

## Installation

```bash
pip install qraft-utils
# or with uv
uv add qraft-utils
```

For local development from the Qraft repository:

```bash
uv pip install ./python/qraft-utils
```

## Usage

1. Add `qraft-utils` to your environment (pip install or local install).
2. Reference it in your model's front-matter:

```sql
---
materialization: table
macros: [qraft_utils]
---
SELECT
    surrogate_key(customer_id, order_date) AS sk_order,
    safe_divide(revenue, order_count)      AS avg_order_value,
    cents_to_dollars(amount_cents)         AS amount_usd
FROM ref('stg_orders')
```

Qraft automatically injects `vars["engine"]` at compile time, so macros adapt their SQL output to the target database.

## Available Macros

### Scalar Transforms (`scalar.py`)

| Function | Description |
|----------|-------------|
| `surrogate_key(*cols)` | MD5-based surrogate key from concatenated columns |
| `generate_surrogate_key(*cols)` | Alias for `surrogate_key` |
| `safe_divide(num, den)` | Division with zero protection (returns NULL on zero) |
| `cents_to_dollars(col)` | Divide by 100.0 |
| `coalesce_zero(col)` | `COALESCE(col, 0)` |
| `bool_or(col)` | Boolean OR aggregation |

### Conditions (`conditions.py`)

| Function | Description |
|----------|-------------|
| `is_valid_email(col)` | Email format validation WHERE clause |
| `recency(date_column, days)` | Date-based recency filter (e.g., last 30 days) |
| `not_deleted(col)` | Soft-delete filter (`col IS NULL`) |
| `accepted_values(col, *values)` | `col IN (...)` filter |

### Structural (`structural.py`)

| Function | Description |
|----------|-------------|
| `pivot(col, values, agg, val_col)` | CASE-WHEN pivot columns |
| `pivot_agg(col, values, agg, val_col)` | Pivot with custom aggregation |
| `union_relations(*relations)` | UNION ALL with source tracking column |
| `star_except(table, *exclude)` | SELECT all columns except named ones (requires `sqlalchemy` and `conn_str` in vars) |

### Date Utilities (`date.py`)

| Function | Description |
|----------|-------------|
| `date_spine(start, end, granularity)` | Generate a date series |
| `fiscal_year_filter(col, start_month)` | Filter for current fiscal year |
| `date_trunc_to(col, granularity)` | Truncate date to given granularity |

## Engine Adaptation

Many macros produce different SQL depending on the target database. The engine is detected from `vars["engine"]` (injected automatically by Qraft at compile time). Supported engines:

- `duckdb` — DuckDB
- `postgres` — PostgreSQL
- `mysql` — MySQL / MariaDB
- `trino` — Trino

If the engine is not recognized, macros fall back to PostgreSQL syntax.

## Local Development Without PyPI

If you are developing locally and `qraft-utils` is not yet on PyPI, you have two options:

**Option 1: Install from the local path**

```bash
uv pip install ./python/qraft-utils
```

**Option 2: Copy the `qraft_utils/` directory into your project's `macros/`**

```
my_project/
  macros/
    qraft_utils/       # Copy from python/qraft-utils/qraft_utils/
      __init__.py
      scalar.py
      conditions.py
      structural.py
      date.py
      engine.py
  models/
    ...
```

Then reference it in your model: `macros: [qraft_utils]`.

## License

MIT
