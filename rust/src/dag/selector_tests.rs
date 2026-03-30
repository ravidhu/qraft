use super::*;
use crate::dag::builder;
use crate::types::ParsedModel;

fn make_dag() -> DagHandle {
    let models = vec![
        ParsedModel {
            name: "a".into(),
            refs: vec![],
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
        ParsedModel {
            name: "c".into(),
            refs: vec!["b".into()],
            sources: vec![],
            tags: vec![],
            materialization: None,
        },
    ];
    builder::build(&models)
}

fn empty_tags() -> HashMap<String, Vec<String>> {
    HashMap::new()
}

#[test]
fn test_select_exact() {
    let dag = make_dag();
    assert_eq!(select(&dag, "b", &empty_tags()), vec!["b"]);
}

#[test]
fn test_select_nonexistent() {
    let dag = make_dag();
    assert!(select(&dag, "z", &empty_tags()).is_empty());
}

#[test]
fn test_select_descendants() {
    let dag = make_dag();
    let result = select(&dag, "a+", &empty_tags());
    assert!(result.contains(&"a".to_string()));
    assert!(result.contains(&"b".to_string()));
    assert!(result.contains(&"c".to_string()));
}

#[test]
fn test_select_ancestors() {
    let dag = make_dag();
    let result = select(&dag, "+c", &empty_tags());
    assert!(result.contains(&"a".to_string()));
    assert!(result.contains(&"b".to_string()));
    assert!(result.contains(&"c".to_string()));
}

#[test]
fn test_select_both() {
    let dag = make_dag();
    let result = select(&dag, "+b+", &empty_tags());
    assert!(result.contains(&"a".to_string()));
    assert!(result.contains(&"b".to_string()));
    assert!(result.contains(&"c".to_string()));
}

#[test]
fn test_select_by_tag() {
    let dag = make_dag();
    let mut tags_map = HashMap::new();
    tags_map.insert("a".to_string(), vec!["staging".to_string()]);
    tags_map.insert("b".to_string(), vec!["staging".to_string(), "daily".to_string()]);

    let result = select(&dag, "tag:staging", &tags_map);
    assert!(result.contains(&"a".to_string()));
    assert!(result.contains(&"b".to_string()));
    assert!(!result.contains(&"c".to_string()));

    let result = select(&dag, "tag:daily", &tags_map);
    assert_eq!(result, vec!["b"]);
}

#[test]
fn test_select_by_tag_no_match() {
    let dag = make_dag();
    let tags_map = HashMap::new();
    assert!(select(&dag, "tag:nonexistent", &tags_map).is_empty());
}
