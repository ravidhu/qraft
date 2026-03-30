# Getting Started

## Installation

Qraft requires Python 3.11+ and a Rust toolchain (rustc 1.70+). All install methods compile the Rust core automatically via [maturin](https://www.maturin.rs/).

```bash
git clone https://github.com/ravidhu/qraft.git
cd qraft
```

### Development mode

Editable install — Python changes take effect immediately:

```bash
make dev
# or directly: uv run maturin develop
```

### Use as a local dependency in another project

From the root of the project that depends on Qraft, point to the Qraft repo root:

```bash
uv add /path/to/qraft
```

Or add it manually to that project's `pyproject.toml`:

```toml
dependencies = [
    "qraft @ file:///absolute/path/to/qraft",
]
```

### Build a wheel

Build a portable `.whl` file from the Qraft repo root:

```bash
uv run maturin build --release
```

Then install it from any project:

```bash
uv pip install /path/to/qraft/rust/target/wheels/qraft-*.whl
```

## Create Your First Project

```bash
qraft init my_project
cd my_project
```

Or initialize in the current directory:

```bash
mkdir my_project && cd my_project
qraft init .
```

This creates:

```
my_project/
  project.yaml       # Project configuration
  models/
    example.sql       # A starter model
  .env.example        # Template for environment variables
  .gitignore
```

## Configure Your Project

Edit `project.yaml`:

```yaml
name: my_project

connection:
  type: duckdb
  path: dev.duckdb

schema: analytics
materialization: view

sources:
  raw:
    schema: raw_data
    tables:
      - customers
      - orders

vars:
  min_order_amount: "0"

environments:
  local:
  prod:
    schema: analytics_prod
    vars:
      min_order_amount: "100"
```

## Write Your First Models

Create `models/stg_customers.sql` (a bronze/staging model):

```sql
SELECT
    id AS customer_id,
    name AS customer_name,
    email,
    created_at
FROM source('raw', 'customers')
```

Create `models/stg_orders.sql`:

```sql
SELECT
    id AS order_id,
    customer_id,
    amount AS order_total,
    created_at AS order_date
FROM source('raw', 'orders')
WHERE amount >= {{ min_order_amount }}
```

Create `models/customer_summary.sql` (a gold model that references the others):

```sql
---
materialization: table
---
SELECT
    c.customer_id,
    c.customer_name,
    COUNT(o.order_id) AS total_orders,
    SUM(o.order_total) AS lifetime_spend
FROM ref('stg_customers') c
LEFT JOIN ref('stg_orders') o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
```

## Validate

Check that all references and sources resolve correctly:

```bash
qraft validate --env local
```

If everything is correct you'll see:

```
All checks passed.
```

If there's a typo, Qraft suggests the closest match:

```
✗ customer_summary  ref('stg_custmers') not found
  → did you mean 'stg_customers'?
```

## Compile

Preview the resolved SQL without executing:

```bash
qraft compile --env local
```

This resolves all `ref()`, `source()`, and `{{ variable }}` expressions and writes compiled SQL to `target/compiled/local/`.

Use `--verbose` to see the full DDL (CREATE VIEW/TABLE statements).

## Run

Execute models against your database in dependency order:

```bash
qraft run --env local
```

Output:

```
  ✓ stg_customers             12ms
  ✓ stg_orders                8ms
  ✓ customer_summary          15ms

Done. 3 models.
```

Models run in topological order. Independent models within the same batch run in parallel.

## Test Your Models

Add data tests to your models using the `columns:` block in front-matter. Update `models/stg_orders.sql`:

```sql
---
columns:
  - name: order_id
    tests:
      - not_null
      - unique
  - name: customer_id
    tests:
      - not_null
  - name: order_total
    tests:
      - accepted_range:
          min_value: 0
---
SELECT
    id AS order_id,
    customer_id,
    amount AS order_total,
    created_at AS order_date
FROM source('raw', 'orders')
WHERE amount >= {{ min_order_amount }}
```

Run the tests:

```bash
qraft test --env local
```

```
  ✓ stg_orders.order_id not_null              0 failures
  ✓ stg_orders.order_id unique                0 failures
  ✓ stg_orders.customer_id not_null           0 failures
  ✓ stg_orders.order_total accepted_range     0 failures

Done. 4 passed.
```

Or use `qraft build` to run models and tests together:

```bash
qraft build --env local
```

## View the DAG

See how your models connect:

```bash
qraft dag
```

```
  source(raw.customers)          → stg_customers
  source(raw.orders)             → stg_orders
  stg_customers                  → customer_summary
  stg_orders                     → customer_summary

3 models, 2 layers.
```

## Next Steps

- [Core Concepts](concepts.md) -- Understand models, the DAG, and environments
- [Configuration](configuration.md) -- Full `project.yaml` reference
- [CLI Reference](cli_reference.md) -- Every command and option
- Try the [examples](../examples/) for more complete projects
