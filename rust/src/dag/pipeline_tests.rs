use super::*;

#[test]
fn test_pipeline_simple() {
    let raw_models = vec![
        RawModel {
            name: "stg_users".into(),
            raw_sql: "SELECT * FROM {{ source('raw', 'users') }}".into(),
        },
        RawModel {
            name: "dim_customers".into(),
            raw_sql: "SELECT * FROM {{ ref('stg_users') }}".into(),
        },
    ];

    let (dag, batches, parsed_models, errors) =
        build_pipeline(&raw_models, &["raw".into()], None);

    // No errors
    assert!(errors.is_empty());

    // 2 models parsed
    assert_eq!(parsed_models.len(), 2);

    // DAG has 2 nodes
    assert_eq!(dag.graph.node_count(), 2);

    // 2 batches: stg_users first, then dim_customers
    assert_eq!(batches.len(), 2);
    assert_eq!(batches[0], vec!["stg_users"]);
    assert_eq!(batches[1], vec!["dim_customers"]);
}

#[test]
fn test_pipeline_with_validation_errors() {
    let raw_models = vec![RawModel {
        name: "broken".into(),
        raw_sql: "SELECT * FROM {{ source('nonexistent', 'table') }}".into(),
    }];

    let (_dag, _batches, _parsed_models, errors) = build_pipeline(&raw_models, &[], None);

    assert!(!errors.is_empty());
    assert_eq!(errors[0].error_type, "missing_source");
}

#[test]
fn test_pipeline_parallel_batches() {
    let raw_models = vec![
        RawModel {
            name: "a".into(),
            raw_sql: "SELECT 1".into(),
        },
        RawModel {
            name: "b".into(),
            raw_sql: "SELECT 2".into(),
        },
        RawModel {
            name: "c".into(),
            raw_sql: "SELECT * FROM {{ ref('a') }} JOIN {{ ref('b') }}".into(),
        },
    ];

    let (_dag, batches, _parsed_models, errors) =
        build_pipeline(&raw_models, &[], None);

    assert!(errors.is_empty());
    // a and b in same batch (no deps), c in next batch
    assert_eq!(batches.len(), 2);
    assert!(batches[0].contains(&"a".to_string()));
    assert!(batches[0].contains(&"b".to_string()));
    assert_eq!(batches[1], vec!["c"]);
}

#[test]
fn test_pipeline_with_select() {
    let raw_models = vec![
        RawModel {
            name: "a".into(),
            raw_sql: "SELECT 1".into(),
        },
        RawModel {
            name: "b".into(),
            raw_sql: "SELECT 2".into(),
        },
        RawModel {
            name: "c".into(),
            raw_sql: "SELECT * FROM {{ ref('a') }} JOIN {{ ref('b') }}".into(),
        },
    ];

    // Select only "a" — should get 1 batch with just "a"
    let (_dag, batches, _parsed_models, errors) =
        build_pipeline(&raw_models, &[], Some("a"));

    assert!(errors.is_empty());
    assert_eq!(batches.len(), 1);
    assert_eq!(batches[0], vec!["a"]);
}

#[test]
fn test_pipeline_with_select_descendants() {
    let raw_models = vec![
        RawModel {
            name: "a".into(),
            raw_sql: "SELECT 1".into(),
        },
        RawModel {
            name: "b".into(),
            raw_sql: "SELECT * FROM {{ ref('a') }}".into(),
        },
        RawModel {
            name: "c".into(),
            raw_sql: "SELECT * FROM {{ ref('b') }}".into(),
        },
    ];

    // Select "a+" — should get a, b, c in proper batch order
    let (_dag, batches, _parsed_models, errors) =
        build_pipeline(&raw_models, &[], Some("a+"));

    assert!(errors.is_empty());
    assert_eq!(batches.len(), 3);
    assert_eq!(batches[0], vec!["a"]);
    assert_eq!(batches[1], vec!["b"]);
    assert_eq!(batches[2], vec!["c"]);
}
