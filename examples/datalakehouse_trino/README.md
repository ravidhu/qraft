# Data Lakehouse — Trino + Iceberg (Base Infrastructure)

This directory provides shared Docker infrastructure for the Trino/Iceberg-based examples. It is **not a standalone Qraft project** — it contains no models or `project.yaml`.

## What's included

- **`docker-compose.base.yml`** — Base Docker Compose with Trino coordinator, Hive Metastore, MinIO (S3-compatible storage), and MariaDB (for Hive Metastore)
- **`catalog/`** — Trino catalog configuration files (Iceberg connector properties)
- **`metadata_init/`** — Database initialization scripts for the Hive Metastore

## Usage

The following example projects extend this base:

- [blog_analytics](../blog_analytics/) — PostgreSQL source, 5 models
- [ecommerce_basic](../ecommerce_basic/) — MariaDB source, 8 models with macros
- [saas_analytics](../saas_analytics/) — Multi-source PostgreSQL, 17 models

Each example has its own `docker-compose.yml` that references this base configuration. To run an example:

```bash
cd ../blog_analytics
docker compose up -d
qraft run --env docker
```

## Architecture

```
Trino (query engine)
  ├── Iceberg catalog (write target)
  │     ├── Hive Metastore (metadata)
  │     └── MinIO (S3 object storage)
  └── Source connectors (read-only)
        ├── PostgreSQL
        └── MariaDB
```

Trino acts as the single query engine. Source databases are accessed through Trino connectors as read-only sources. Models are materialized into the Iceberg catalog backed by MinIO storage.
