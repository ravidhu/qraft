use super::*;

fn no_fm() -> Option<HashMap<String, String>> {
    None
}

fn no_eph() -> HashMap<String, EphemeralModel> {
    HashMap::new()
}

#[test]
fn test_resolve_refs() {
    let body = "SELECT * FROM ref('stg_orders')";
    let result = resolve(
        body, body, "fct_revenue", "analytics", "view",
        &HashMap::new(), &HashMap::new(),
        &["stg_orders".to_string()], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    assert!(result.compiled_sql.contains("analytics.stg_orders"));
}

#[test]
fn test_resolve_sources() {
    let body = "SELECT * FROM source('raw', 'orders')";
    let mut sources = HashMap::new();
    sources.insert("raw".to_string(), SourceInfo {
        database: "".to_string(),
        schema: "main".to_string(),
    });
    let result = resolve(
        body, body, "stg_orders", "analytics", "view",
        &HashMap::new(), &sources,
        &[], &[("raw".to_string(), "orders".to_string())],
        &no_fm(), &no_eph(),
    ).unwrap();
    assert!(result.compiled_sql.contains("main.orders"));
}

#[test]
fn test_resolve_vars() {
    let body = "SELECT * FROM {{ schema }}.table WHERE amount > {{ min_amount }}";
    let mut vars = HashMap::new();
    vars.insert("min_amount".to_string(), "100".to_string());
    let result = resolve(
        body, body, "test", "analytics", "view",
        &vars, &HashMap::new(), &[], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    assert!(result.compiled_sql.contains("analytics.table"));
    assert!(result.compiled_sql.contains("> 100"));
}

#[test]
fn test_unresolved_var_error() {
    let body = "SELECT * FROM {{ unknown_var }}.table";
    let result = resolve(
        body, body, "test", "analytics", "view",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &no_fm(), &no_eph(),
    );
    assert!(result.is_err());
}

#[test]
fn test_ddl_view() {
    let body = "SELECT 1";
    let result = resolve(
        body, body, "test", "analytics", "view",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    assert!(result.ddl.starts_with("CREATE OR REPLACE VIEW"));
}

#[test]
fn test_ddl_table() {
    let body = "SELECT 1";
    let result = resolve(
        body, body, "test", "analytics", "table",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    assert!(result.ddl.contains("DROP TABLE IF EXISTS"));
    assert!(result.ddl.contains("CREATE TABLE"));
}

#[test]
fn test_ddl_materialized_view() {
    let body = "SELECT 1";
    let result = resolve(
        body, body, "test", "analytics", "materialized_view",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    assert!(result.ddl.contains("CREATE MATERIALIZED VIEW IF NOT EXISTS"));
}

#[test]
fn test_ddl_ephemeral_empty() {
    let body = "SELECT 1";
    let result = resolve(
        body, body, "test", "analytics", "ephemeral",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    assert!(result.ddl.is_empty());
}

#[test]
fn test_ephemeral_single_cte() {
    let body = "SELECT * FROM ref('date_spine')";
    let mut ephemerals = HashMap::new();
    ephemerals.insert("date_spine".to_string(), EphemeralModel {
        name: "date_spine".to_string(),
        compiled_body: "SELECT generate_series(1, 10) AS date_day".to_string(),
        deps: vec![],
    });
    let result = resolve(
        body, body, "summary", "analytics", "view",
        &HashMap::new(), &HashMap::new(),
        &["date_spine".to_string()], &[],
        &no_fm(), &ephemerals,
    ).unwrap();
    assert!(result.compiled_sql.contains("WITH date_spine AS ("));
    assert!(result.compiled_sql.contains("SELECT generate_series(1, 10) AS date_day"));
    assert!(result.compiled_sql.contains("FROM date_spine"));
    assert!(!result.compiled_sql.contains("analytics.date_spine"));
}

#[test]
fn test_ephemeral_transitive() {
    let mut ephemerals = HashMap::new();
    ephemerals.insert("base".to_string(), EphemeralModel {
        name: "base".to_string(),
        compiled_body: "SELECT 1 AS id".to_string(),
        deps: vec![],
    });
    ephemerals.insert("mid".to_string(), EphemeralModel {
        name: "mid".to_string(),
        compiled_body: "SELECT id FROM base".to_string(),
        deps: vec!["base".to_string()],
    });

    let body = "SELECT * FROM ref('mid')";
    let result = resolve(
        body, body, "final", "analytics", "view",
        &HashMap::new(), &HashMap::new(),
        &["mid".to_string()], &[],
        &no_fm(), &ephemerals,
    ).unwrap();
    // base CTE should come before mid CTE
    let base_pos = result.compiled_sql.find("base AS (").unwrap();
    let mid_pos = result.compiled_sql.find("mid AS (").unwrap();
    assert!(base_pos < mid_pos);
}

#[test]
fn test_ephemeral_dedup() {
    let mut ephemerals = HashMap::new();
    ephemerals.insert("shared".to_string(), EphemeralModel {
        name: "shared".to_string(),
        compiled_body: "SELECT 1 AS val".to_string(),
        deps: vec![],
    });
    let body = "SELECT * FROM ref('shared') UNION ALL SELECT * FROM ref('shared')";
    let result = resolve(
        body, body, "consumer", "analytics", "view",
        &HashMap::new(), &HashMap::new(),
        &["shared".to_string(), "shared".to_string()], &[],
        &no_fm(), &ephemerals,
    ).unwrap();
    // Should only have one CTE
    assert_eq!(result.compiled_sql.matches("shared AS (").count(), 1);
}

#[test]
fn test_description_propagated() {
    let body = "SELECT 1";
    let mut fm = HashMap::new();
    fm.insert("description".to_string(), "My model description".to_string());
    let result = resolve(
        body, body, "test", "analytics", "view",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &Some(fm), &no_eph(),
    ).unwrap();
    assert_eq!(result.description, Some("My model description".to_string()));
}

#[test]
fn test_tags_propagated() {
    let body = "SELECT 1";
    let mut fm = HashMap::new();
    fm.insert("tags".to_string(), "staging,daily".to_string());
    let result = resolve(
        body, body, "test", "analytics", "view",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &Some(fm), &no_eph(),
    ).unwrap();
    assert_eq!(result.tags, vec!["staging", "daily"]);
}

#[test]
fn test_schema_override() {
    let body = "SELECT * FROM ref('stg_orders')";
    let mut fm = HashMap::new();
    fm.insert("schema".to_string(), "custom_schema".to_string());
    let result = resolve(
        body, body, "test", "analytics", "view",
        &HashMap::new(), &HashMap::new(),
        &["stg_orders".to_string()], &[],
        &Some(fm), &no_eph(),
    ).unwrap();
    assert!(result.compiled_sql.contains("custom_schema.stg_orders"));
    assert!(result.target.starts_with("custom_schema."));
}

#[test]
fn test_invalid_materialization_error() {
    let body = "SELECT 1";
    let result = resolve(
        body, body, "test", "analytics", "nonexistent",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &no_fm(), &no_eph(),
    );
    assert!(result.is_err());
}

#[test]
fn test_table_incremental_append() {
    let body = "SELECT * FROM source_table";
    let result = resolve(
        body, body, "test", "analytics", "table_incremental",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    assert!(result.ddl.contains("INSERT INTO"));
}

#[test]
fn test_table_incremental_with_unique_key() {
    let body = "SELECT id, name FROM source_table";
    let mut fm = HashMap::new();
    fm.insert("materialization".to_string(), "table_incremental".to_string());
    fm.insert("unique_key".to_string(), "id".to_string());
    let result = resolve(
        body, body, "test", "analytics", "table_incremental",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &Some(fm), &no_eph(),
    ).unwrap();
    assert!(result.ddl.contains("DELETE FROM"));
    assert!(result.ddl.contains("INSERT INTO"));
}

#[test]
fn test_ephemeral_with_existing_with() {
    let body = "WITH existing AS (SELECT 1) SELECT * FROM existing, ref('eph')";
    let mut ephemerals = HashMap::new();
    ephemerals.insert("eph".to_string(), EphemeralModel {
        name: "eph".to_string(),
        compiled_body: "SELECT 2 AS val".to_string(),
        deps: vec![],
    });
    let result = resolve(
        body, body, "test", "analytics", "view",
        &HashMap::new(), &HashMap::new(),
        &["eph".to_string()], &[],
        &no_fm(), &ephemerals,
    ).unwrap();
    // Should merge CTEs
    assert!(result.compiled_sql.contains("eph AS ("));
    assert!(result.compiled_sql.contains("existing AS (SELECT 1)"));
    // Only one WITH keyword
    assert_eq!(result.compiled_sql.matches("WITH ").count(), 1);
}

// ── Phase 1 tests: resolve_sql + wrap_ddl split ──

#[test]
fn test_resolve_sql_returns_sql_without_ddl() {
    let body = "SELECT 1";
    let resolved = resolve_sql(
        body, "test", "analytics", "view",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    assert_eq!(resolved.resolved_sql, "SELECT 1");
    assert_eq!(resolved.target, "analytics.test");
    assert_eq!(resolved.materialization, "view");
}

#[test]
fn test_wrap_ddl_generates_correct_ddl() {
    let resolved = ResolvedModel {
        name: "test".to_string(),
        resolved_sql: "SELECT 1".to_string(),
        target: "analytics.test".to_string(),
        materialization: "view".to_string(),
        refs: vec![],
        sources: vec![],
        macros: vec![],
        description: None,
        tags: vec![],
        enabled: true,
        unique_key: None,
    };
    let compiled = wrap_ddl(&resolved).unwrap();
    assert!(compiled.ddl.starts_with("CREATE OR REPLACE VIEW"));
    assert_eq!(compiled.compiled_sql, "SELECT 1");
}

#[test]
fn test_round_trip_matches_original() {
    // resolve_sql + wrap_ddl should produce the same result as resolve
    let body = "SELECT * FROM ref('stg_orders')";
    let old = resolve(
        body, body, "fct_revenue", "analytics", "view",
        &HashMap::new(), &HashMap::new(),
        &["stg_orders".to_string()], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    let resolved = resolve_sql(
        body, "fct_revenue", "analytics", "view",
        &HashMap::new(), &HashMap::new(),
        &["stg_orders".to_string()], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    let new = wrap_ddl(&resolved).unwrap();
    assert_eq!(old.compiled_sql, new.compiled_sql);
    assert_eq!(old.ddl, new.ddl);
    assert_eq!(old.target, new.target);
}

#[test]
fn test_macros_extracted_from_front_matter() {
    let body = "SELECT 1";
    let mut fm = HashMap::new();
    fm.insert("macros".to_string(), "common_transforms,schema_utils".to_string());
    let resolved = resolve_sql(
        body, "test", "analytics", "view",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &Some(fm), &no_eph(),
    ).unwrap();
    assert_eq!(resolved.macros, vec!["common_transforms", "schema_utils"]);
}

#[test]
fn test_macros_empty_when_not_declared() {
    let body = "SELECT 1";
    let resolved = resolve_sql(
        body, "test", "analytics", "view",
        &HashMap::new(), &HashMap::new(), &[], &[],
        &no_fm(), &no_eph(),
    ).unwrap();
    assert!(resolved.macros.is_empty());
}
