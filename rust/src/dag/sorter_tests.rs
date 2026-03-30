use super::*;
use crate::dag::builder;
use crate::types::ParsedModel;

#[test]
fn test_topo_sort_linear() {
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
    let dag = builder::build(&models);
    let batches = topo_sort_batches(&dag);
    assert_eq!(batches.len(), 3);
    assert_eq!(batches[0], vec!["a"]);
    assert_eq!(batches[1], vec!["b"]);
    assert_eq!(batches[2], vec!["c"]);
}

#[test]
fn test_topo_sort_parallel() {
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
            refs: vec![],
            sources: vec![],
            tags: vec![],
            materialization: None,
        },
        ParsedModel {
            name: "c".into(),
            refs: vec!["a".into(), "b".into()],
            sources: vec![],
            tags: vec![],
            materialization: None,
        },
    ];
    let dag = builder::build(&models);
    let batches = topo_sort_batches(&dag);
    assert_eq!(batches.len(), 2);
    // First batch has a and b (parallel)
    assert_eq!(batches[0].len(), 2);
    assert!(batches[0].contains(&"a".to_string()));
    assert!(batches[0].contains(&"b".to_string()));
    // Second batch has c
    assert_eq!(batches[1], vec!["c"]);
}

#[test]
fn test_topo_sort_single() {
    let models = vec![ParsedModel {
        name: "a".into(),
        refs: vec![],
        sources: vec![],
        tags: vec![],
        materialization: None,
    }];
    let dag = builder::build(&models);
    let batches = topo_sort_batches(&dag);
    assert_eq!(batches, vec![vec!["a".to_string()]]);
}
