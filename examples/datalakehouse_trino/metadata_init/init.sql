-- ============================================================================
-- Iceberg JDBC Catalog — Metadata Table Initialization
-- ============================================================================
--
-- WHY THIS FILE EXISTS
--
-- The Iceberg JDBC catalog stores table metadata in two PostgreSQL tables:
-- iceberg_tables and iceberg_namespace_properties. Apache Iceberg's own
-- JdbcCatalog.initialize() can auto-create these tables when the property
-- jdbc.init-catalog-tables=true (the default). However, Trino's Iceberg
-- connector does NOT enable this auto-init — the Trino docs explicitly state:
--
--   "The JDBC catalog requires the metadata tables to already exist."
--   — https://trino.io/docs/current/object-storage/metastores.html
--
-- So we pre-create them here via docker-entrypoint-initdb.d on the
-- metadata_db PostgreSQL container.
--
-- SCHEMA SOURCE
--
-- DDL taken from Apache Iceberg's JdbcUtil.java:
-- https://github.com/apache/iceberg/blob/main/core/src/main/java/org/apache/iceberg/jdbc/JdbcUtil.java
--
-- iceberg_tables:
--   V0 schema  — V0_CREATE_CATALOG_SQL (base columns)
--   V1 addition — V1_UPDATE_CATALOG_SQL (adds record_type VARCHAR(5) for view support)
--   Trino defaults iceberg.jdbc-catalog.schema-version=V1, so we include
--   record_type in the CREATE TABLE directly instead of a separate ALTER.
--
-- iceberg_namespace_properties:
--   CREATE_NAMESPACE_PROPERTIES_TABLE_SQL (unchanged across versions)
--
-- ============================================================================

CREATE TABLE IF NOT EXISTS iceberg_tables (
    catalog_name               VARCHAR(255) NOT NULL,
    table_namespace            VARCHAR(255) NOT NULL,
    table_name                 VARCHAR(255) NOT NULL,
    metadata_location          VARCHAR(1000),
    previous_metadata_location VARCHAR(1000),
    record_type                VARCHAR(5),
    PRIMARY KEY (catalog_name, table_namespace, table_name)
);

CREATE TABLE IF NOT EXISTS iceberg_namespace_properties (
    catalog_name   VARCHAR(255)  NOT NULL,
    namespace      VARCHAR(255)  NOT NULL,
    property_key   VARCHAR(255),
    property_value VARCHAR(1000),
    PRIMARY KEY (catalog_name, namespace, property_key)
);
