# CLI Reference

## Global Usage

```
qraft <command> [options]
```

## Commands

### `qraft init`

Create a new Qraft project with starter files.

```bash
qraft init <project_name>
```

**Creates:**
- `<project_name>/project.yaml` — Default config with DuckDB connection
- `<project_name>/models/example.sql` — Starter model
- `<project_name>/macros/` — Directory for custom macros
- `<project_name>/.env.example` — Environment variable template
- `<project_name>/.gitignore` — Ignores `.env`, DuckDB files

**Example:**

```bash
qraft init sales_analytics
cd sales_analytics
```

---

### `qraft compile`

Resolve all templating and write compiled SQL to `target/`.

```bash
qraft compile --env <environment> [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--env` | Target environment (required) |
| `--select <pattern>` | Only compile models matching the pattern |
| `--verbose` | Show DDL (CREATE statements) instead of just the SQL body |

**Output:** Prints compiled SQL to the console, writes files to `target/compiled/<env>/`, and generates `target/manifest.json` with model metadata and dependency graph.

**Note:** Compilation is done in batch — all models are resolved in a single Rust call, then macros are expanded in Python, then DDL is wrapped in a second Rust call.

**Examples:**

```bash
# Compile all models for local environment
qraft compile --env local

# Compile a specific model and its descendants
qraft compile --env prod --select "stg_orders+"

# Show full DDL statements
qraft compile --env local --verbose
```

---

### `qraft run`

Compile and execute models against the database in dependency order.

```bash
qraft run --env <environment> [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--env` | -- | Target environment (required) |
| `--select <pattern>` | -- | Only run models matching the pattern |
| `--parallel <n>` | `4` | Maximum models to run concurrently within a batch. **Note:** DuckDB is automatically capped to 1 due to its exclusive file lock — this is not an error. |
| `--dry-run` | `false` | Compile and show plan without executing |
| `--verbose` | `false` | Show detailed execution logs |

**Execution flow:**
1. Load config, resolve environment
2. Scan models, build DAG pipeline (parse, validate, sort, select — single Rust call)
3. Batch-compile all selected models (resolve → macros → wrap DDL)
4. Write compiled SQL to `target/` and generate `target/manifest.json`
5. Execute batches in topological order with parallelism

**Examples:**

```bash
# Run everything
qraft run --env local

# Dry run to preview
qraft run --env prod --dry-run

# Run with more parallelism
qraft run --env local --parallel 8

# Run a subset
qraft run --env local --select "+customer_summary"
```

**Output:**

```
  ✓ stg_customers             12ms
  ✓ stg_orders                8ms
  ✓ customer_summary          15ms

Done. 3 models.
```

If a model fails, downstream models that depend on it are skipped:

```
  ✓ stg_customers             12ms
  ✗ stg_orders                SQL error: column not found
  ⊘ customer_summary          SKIPPED

Failed. 1 ok, 1 failed, 1 skipped.
```

---

### `qraft dag`

Display the dependency graph. No environment or database connection required — only reads SQL files.

```bash
qraft dag
```

**Output:**

```
  source(raw.customers)          → stg_customers
  source(raw.orders)             → stg_orders
  stg_customers                  → customer_summary
  stg_orders                     → customer_summary

3 models, 2 layers.
```

Shows each dependency edge (sources and refs) and the total model/layer count. Uses `build_pipeline()` to parse and sort models in a single Rust call.

---

### `qraft validate`

Check your project for errors without executing anything.

```bash
qraft validate --env <environment>
```

**Checks:**
- Missing `ref()` targets (model doesn't exist)
- Undeclared `source()` names (not in `project.yaml`)
- Circular dependencies (cycles in the DAG)

**On success:**

```
All checks passed.
```

**On failure:**

```
✗ customer_summary  ref('stg_custmers') not found
  → did you mean 'stg_customers'?
✗ order_totals  source('raw_dat') not declared in project.yaml
  → did you mean 'raw'?
```

Qraft uses fuzzy matching to suggest corrections for typos.

---

### `qraft clean`

Drop all managed objects (views/tables) from the database.

```bash
qraft clean --env <environment> [--yes]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--env` | Target environment (required) |
| `--yes` | Skip the confirmation prompt |

**Behavior:** Lists all models that will be dropped and asks for confirmation. Use `--yes` to skip the prompt (useful in scripts).

```bash
# Interactive
qraft clean --env local

# Non-interactive
qraft clean --env staging --yes
```

---

### `qraft test-connection`

Verify that the database connection works.

```bash
qraft test-connection --env <environment>
```

```bash
qraft test-connection --env local
# ✓ Connected to DuckDB (dev.duckdb)

qraft test-connection --env prod
# ✗ Connection failed: timeout
```

### `qraft test`

Run data tests defined in model front-matter.

```bash
qraft test --env <environment> [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--env` | -- | Target environment (required) |
| `--select <pattern>` | -- | Only test models matching the pattern |
| `--fail-fast` | `false` | Stop on first test failure |

**Behavior:** Discovers all test definitions from `columns:` blocks in model front-matter, generates test SQL, and executes each test against the database. A test passes when it returns zero rows (rows = failures).

**Examples:**

```bash
# Test all models
qraft test --env local

# Test a specific model
qraft test --env local --select "stg_orders"

# Test all staging models
qraft test --env local --select "stg_*"

# Test all models tagged "daily"
qraft test --env local --select "tag:daily"
```

**Output:**

```
  ✓ stg_customers.customer_id not_null         0 failures
  ✓ stg_customers.customer_id unique           0 failures
  ✓ stg_orders.order_id not_null               0 failures
  ⚠ stg_orders.status accepted_values          2 failures (warn)

Done. 3 passed, 1 warning.
```

Tests with `severity: warn` report failures but do not cause a non-zero exit code. Tests with `severity: error` (the default) cause exit code 1 on failure.

---

### `qraft build`

Run models and then run tests — equivalent to `qraft run` followed by `qraft test`.

```bash
qraft build --env <environment> [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--env` | -- | Target environment (required) |
| `--select <pattern>` | -- | Only build models matching the pattern |
| `--parallel <n>` | `4` | Maximum models to run concurrently within a batch |
| `--verbose` | `false` | Show detailed execution logs |
| `--fail-fast` | `false` | Stop on first test failure |

**Behavior:**
1. Runs all selected models (same as `qraft run`)
2. Runs all data tests on the selected models (same as `qraft test`)

If a model fails to run, its tests are skipped. Exit code is non-zero if any model fails or any error-severity test fails.

```bash
# Build everything
qraft build --env local

# Build and test a subset
qraft build --env local --select "stg_orders+"
```

---

### `qraft docs generate`

Generate an interactive catalog site from your project's compiled manifest.

```bash
qraft docs generate --env <environment> [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--env` | -- | Target environment (required) |
| `--select <pattern>` | -- | Only include models matching the pattern |
| `--target-dir` | `target` | Directory where catalog files are written |

**Behavior:** If a `target/manifest.json` already exists (from a prior `compile` or `run`), the catalog is generated directly from it. If no manifest is found, Qraft compiles the project first to produce one.

The catalog is a pre-built React SPA that visualizes your model lineage graph, model details, column descriptions, and test definitions. Output is written to `<target-dir>/catalog/`.

```bash
# Generate catalog for local environment
qraft docs generate --env local

# Generate catalog for a subset of models
qraft docs generate --env prod --select "stg_*"
```

---

### `qraft docs serve`

Start a local HTTP server to view the generated catalog.

```bash
qraft docs serve [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | `8080` | Port to serve on |
| `--target-dir` | `target` | Directory containing the catalog |

**Prerequisite:** Run `qraft docs generate --env <env>` first. If the catalog directory doesn't exist, the command exits with an error.

```bash
# Serve the catalog on default port
qraft docs serve

# Serve on a custom port
qraft docs serve --port 3000
```

---

### `qraft show`

Show compiled SQL for a single model.

```bash
qraft show --env <environment> <model_name> [--expanded]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--env` | Target environment (required) |
| `--expanded` | Show post-macro expansion SQL |

**Examples:**

```bash
# Show compiled SQL for a model
qraft show --env local stg_orders

# Show SQL after macro expansion
qraft show --env local fct_customer_summary --expanded
```

Without `--expanded`, shows the compiled SQL with refs and variables resolved. With `--expanded`, additionally expands macro calls so you can see the final SQL that would be executed.

---

## Selection Patterns

Several commands accept a `--select` option. The pattern syntax:

| Pattern | Selects |
|---------|---------|
| `model_name` | Exact model |
| `model+` | Model + all downstream descendants |
| `+model` | All upstream ancestors + model |
| `+model+` | Ancestors + model + descendants |
| `tag:name` | All models with the given tag (set in front-matter) |
| `prefix*` | All models with names starting with the prefix |

**Examples:**

```bash
# Run only stg_orders and everything that depends on it
qraft run --env local --select "stg_orders+"

# Run customer_summary and everything it needs
qraft run --env local --select "+customer_summary"

# Compile all staging models
qraft compile --env local --select "stg_*"

# Run all models tagged as "daily"
qraft run --env local --select "tag:daily"
```
