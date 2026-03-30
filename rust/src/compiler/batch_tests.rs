use std::collections::HashMap;

use super::*;
use crate::types::SourceInfo;

fn make_sources() -> HashMap<String, SourceInfo> {
    let mut sources = HashMap::new();
    sources.insert(
        "raw".to_string(),
        SourceInfo {
            database: String::new(),
            schema: "raw_data".to_string(),
        },
    );
    sources
}

#[test]
fn test_batch_resolve_basic() {
    let models = vec![
        RawModelInput {
            name: "stg_users".into(),
            raw_sql: "SELECT * FROM source('raw', 'users')".into(),
        },
        RawModelInput {
            name: "dim_customers".into(),
            raw_sql: "SELECT * FROM ref('stg_users') WHERE active = true".into(),
        },
    ];

    let results = batch_resolve(
        &models,
        "analytics",
        "view",
        &HashMap::new(),
        &make_sources(),
        &HashMap::new(),
    )
    .unwrap();

    assert_eq!(results.len(), 2);
    assert!(results[0].resolved_sql.contains("raw_data.users"));
    assert!(results[1].resolved_sql.contains("analytics.stg_users"));
}

#[test]
fn test_batch_resolve_with_vars() {
    let models = vec![RawModelInput {
        name: "filtered".into(),
        raw_sql: "SELECT * FROM t WHERE region = '{{ region }}'".into(),
    }];

    let mut vars = HashMap::new();
    vars.insert("region".to_string(), "us_west".to_string());

    let results = batch_resolve(
        &models,
        "analytics",
        "view",
        &vars,
        &HashMap::new(),
        &HashMap::new(),
    )
    .unwrap();

    assert!(results[0].resolved_sql.contains("us_west"));
}

#[test]
fn test_batch_wrap_ddl_basic() {
    let models = vec![
        RawModelInput {
            name: "stg_users".into(),
            raw_sql: "SELECT * FROM source('raw', 'users')".into(),
        },
        RawModelInput {
            name: "dim_customers".into(),
            raw_sql: "---\nmaterialization: table\n---\nSELECT * FROM ref('stg_users')".into(),
        },
    ];

    let resolved = batch_resolve(
        &models,
        "analytics",
        "view",
        &HashMap::new(),
        &make_sources(),
        &HashMap::new(),
    )
    .unwrap();

    let compiled = batch_wrap_ddl(&resolved).unwrap();

    assert_eq!(compiled.len(), 2);
    assert!(compiled[0].ddl.contains("CREATE OR REPLACE VIEW"));
    assert!(compiled[1].ddl.contains("CREATE TABLE"));
}
