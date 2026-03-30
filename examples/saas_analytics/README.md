# SaaS Analytics

A comprehensive example demonstrating multi-source projects, per-model schema overrides, custom macros, and a 4-layer DAG. Reads from PostgreSQL via Trino, writes to an Iceberg lakehouse.

## Data Model

Nine raw source tables across three systems feed a 17-model pipeline:

```mermaid
graph LR
    subgraph PostgreSQL
        subgraph CRM
            CA[crm.accounts]
            CC[crm.contacts]
            CO[crm.opportunities]
        end

        subgraph Billing
            BS[billing.subscriptions]
            BI[billing.invoices]
            BP[billing.payments]
        end

        subgraph Product
            PU[product.users]
            PE[product.events]
            PF[product.feature_usage]
        end
    end

    T{{Trino}}

    subgraph Iceberg
        subgraph Staging
            SA[stg_accounts]
            SC[stg_contacts]
            SO[stg_opportunities]
            SS[stg_subscriptions]
            SI[stg_invoices]
            SP[stg_payments]
            SU[stg_users]
            SE[stg_events]
            SF[stg_feature_usage]
        end

        subgraph Intermediate
            IA[int_accounts_enriched]
            IR[int_revenue_by_account]
            IS[int_sales_pipeline fa:fa-ghost]
            IP[int_product_engagement fa:fa-ghost]
        end

        subgraph Gold
            FM[fct_mrr_summary]
            FH[fct_account_health]
            FP[fct_product_adoption]
            DA[dim_account]
        end
    end

    CA -- source --> T
    CC -- source --> T
    CO -- source --> T
    BS -- source --> T
    BI -- source --> T
    BP -- source --> T
    PU -- source --> T
    PE -- source --> T
    PF -- source --> T

    T -- read/write --> SA
    T -- read/write --> SC
    T -- read/write --> SO
    T -- read/write --> SS
    T -- read/write --> SI
    T -- read/write --> SP
    T -- read/write --> SU
    T -- read/write --> SE
    T -- read/write --> SF

    SA --> IA
    SS --> IA
    SC --> IA
    SU --> IA

    SS --> IR
    SI --> IR
    SP --> IR

    SO --> IS

    SU --> IP
    SE --> IP
    SF --> IP

    IA --> FM
    IA --> FH
    IR --> FH
    IS --> FH
    IP --> FH

    FH --> FP

    IA --> DA
```

| Layer            | Models | Description |
|------------------|--------|-------------|
| staging (9)      | `stg_accounts`, `stg_contacts`, `stg_opportunities`, `stg_subscriptions`, `stg_invoices`, `stg_payments`, `stg_users`, `stg_events`, `stg_feature_usage` | Clean and rename |
| intermediate (4) | `int_accounts_enriched`, `int_revenue_by_account`, `int_sales_pipeline`, `int_product_engagement` | Cross-source joins |
| gold (4)         | `fct_mrr_summary`, `fct_account_health`, `fct_product_adoption`, `dim_account` | Business metrics and dimensions |

### Notable Features

- **Multiple data sources**: CRM, billing, and product telemetry systems.
- **Per-model schema override**: `dim_account` writes to a `dimensions` schema instead of the default `analytics` schema.
- **Custom macros**: `saas_utils.py` provides `health_score()` and `revenue_tier()`.
- **`qraft_utils` macros**: `fct_account_health` uses macros from the shared library.
- **4-layer DAG**: `fct_product_adoption` depends on `fct_account_health`, creating a fourth layer.

## Prerequisites

Install the `qraft-utils` macro library (from the repo root):

```bash
uv pip install -e python/qraft-utils/
```

## Quick Start

```bash
cd examples/saas_analytics

# 1. Start the Docker stack (PostgreSQL source + Trino + Iceberg)
docker compose up -d

# 2. Validate the project
qraft validate --env docker

# 3. View the dependency graph
qraft dag

# 4. Compile SQL (preview without executing)
qraft compile --env docker

# 5. Run all models
qraft run --env docker
```

## Environments

| Environment | Engine | Notes                                 |
|-------------|--------|---------------------------------------|
| `docker`    | Trino  | PostgreSQL source + Iceberg target    |
| `staging`   | Trino  | Uses `analytics_staging` schema       |
| `prod`      | Trino  | Overrides `churn_inactive_days` to 60 |

## Project Variables

| Variable                  | Default | Description                        |
|---------------------------|---------|------------------------------------|
| `trial_days`              | `14`    | Trial period length                |
| `churn_inactive_days`     | `30`    | Days of inactivity before churn    |
| `mrr_currency`            | `USD`   | Currency for MRR reporting         |
| `healthy_mrr_threshold`   | `10000` | MRR threshold for "healthy" status |
| `at_risk_event_threshold` | `5`     | Min events before flagging at-risk |
