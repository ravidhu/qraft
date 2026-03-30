use super::*;

#[test]
fn test_build_simple_dag() {
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
    ];
    let dag = build(&models);
    assert_eq!(dag.graph.node_count(), 2);
    assert_eq!(dag.graph.edge_count(), 1);
}

#[test]
fn test_build_dag_with_missing_ref() {
    let models = vec![ParsedModel {
        name: "a".into(),
        refs: vec!["nonexistent".into()],
        sources: vec![],
        tags: vec![],
        materialization: None,
    }];
    let dag = build(&models);
    assert_eq!(dag.graph.node_count(), 1);
    assert_eq!(dag.graph.edge_count(), 0); // missing ref ignored
}
