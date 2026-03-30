use petgraph::visit::Bfs;
use std::collections::{HashMap, HashSet};

use crate::types::DagHandle;

/// Select models by a dbt-like pattern
pub fn select(dag: &DagHandle, pattern: &str, tags_map: &HashMap<String, Vec<String>>) -> Vec<String> {
    if pattern.ends_with('+') && pattern.starts_with('+') {
        // +model+ : ancestors + model + descendants
        let model = pattern.trim_matches('+');
        let mut result = get_ancestors(dag, model);
        result.insert(model.to_string());
        result.extend(get_descendants(dag, model));
        result.into_iter().collect()
    } else if pattern.ends_with('+') {
        // model+ : model + descendants
        let model = pattern.trim_end_matches('+');
        let mut result = get_descendants(dag, model);
        result.insert(model.to_string());
        result.into_iter().collect()
    } else if pattern.starts_with('+') {
        // +model : ancestors + model
        let model = pattern.trim_start_matches('+');
        let mut result = get_ancestors(dag, model);
        result.insert(model.to_string());
        result.into_iter().collect()
    } else if pattern.ends_with("/*") {
        // folder/* : all models whose name starts with the prefix
        let prefix = pattern.trim_end_matches("/*");
        dag.node_map
            .keys()
            .filter(|name| name.starts_with(prefix))
            .cloned()
            .collect()
    } else if pattern.starts_with("tag:") {
        let tag = &pattern[4..];
        tags_map
            .iter()
            .filter(|(name, tags)| {
                tags.iter().any(|t| t == tag) && dag.node_map.contains_key(*name)
            })
            .map(|(name, _)| name.clone())
            .collect()
    } else {
        // Exact name
        if dag.node_map.contains_key(pattern) {
            vec![pattern.to_string()]
        } else {
            Vec::new()
        }
    }
}

fn get_descendants(dag: &DagHandle, model: &str) -> HashSet<String> {
    let mut result = HashSet::new();
    if let Some(&start) = dag.node_map.get(model) {
        let mut bfs = Bfs::new(&dag.graph, start);
        while let Some(node) = bfs.next(&dag.graph) {
            let name = &dag.graph[node];
            if name != model {
                result.insert(name.clone());
            }
        }
    }
    result
}

fn get_ancestors(dag: &DagHandle, model: &str) -> HashSet<String> {
    let mut result = HashSet::new();
    if let Some(&start) = dag.node_map.get(model) {
        // BFS on the reversed graph
        let reversed = petgraph::visit::Reversed(&dag.graph);
        let mut bfs = Bfs::new(&reversed, start);
        while let Some(node) = bfs.next(&reversed) {
            let name = &dag.graph[node];
            if name != model {
                result.insert(name.clone());
            }
        }
    }
    result
}

#[cfg(test)]
#[path = "selector_tests.rs"]
mod tests;
