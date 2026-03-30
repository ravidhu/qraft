use super::*;
use crate::dag::builder;

#[test]
fn test_validate_missing_ref() {
    let models = vec![ParsedModel {
        name: "a".into(),
        refs: vec!["nonexistent".into()],
        sources: vec![],
        tags: vec![],
        materialization: None,
    }];
    let dag = builder::build(&models);
    let errors = validate(&dag, &models, &[]);
    assert_eq!(errors.len(), 1);
    assert_eq!(errors[0].error_type, "missing_ref");
}

#[test]
fn test_validate_missing_source() {
    let models = vec![ParsedModel {
        name: "a".into(),
        refs: vec![],
        sources: vec![("raw_data".into(), "orders".into())],
        tags: vec![],
        materialization: None,
    }];
    let dag = builder::build(&models);
    let errors = validate(&dag, &models, &[]);
    assert_eq!(errors.len(), 1);
    assert_eq!(errors[0].error_type, "missing_source");
}

#[test]
fn test_validate_cycle() {
    let models = vec![
        ParsedModel {
            name: "a".into(),
            refs: vec!["b".into()],
            sources: vec![],
            tags: vec![],
            materialization: None,
        },
        ParsedModel {
            name: "b".into(),
            refs: vec!["a".into()],
            sources: vec![],
            tags: vec![],
            materialization: None,
        },
    ];
    let dag = builder::build(&models);
    let errors = validate(&dag, &models, &[]);
    assert!(errors.iter().any(|e| e.error_type == "cycle"));
}

#[test]
fn test_validate_all_ok() {
    let models = vec![
        ParsedModel {
            name: "a".into(),
            refs: vec![],
            sources: vec![("raw".into(), "orders".into())],
            tags: vec![],
            materialization: None,
        },
        ParsedModel {
            name: "b".into(),
            refs: vec!["a".into()],
            sources: vec![],
            tags: vec![],
            materialization: None,
        },
    ];
    let dag = builder::build(&models);
    let errors = validate(&dag, &models, &["raw".to_string()]);
    assert!(errors.is_empty());
}

#[test]
fn test_fuzzy_suggestion() {
    let result = fuzzy_suggest("stg_ordrs", &["stg_orders", "stg_customers"], 0.8);
    assert_eq!(result, Some("stg_orders".to_string()));
}
