use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::visit::EdgeRef;
use std::collections::HashMap;

use crate::types::{DagHandle, ParsedModel};

/// Build a DAG from a list of parsed models
pub fn build(models: &[ParsedModel]) -> DagHandle {
    let mut graph = DiGraph::new();
    let mut node_map: HashMap<String, NodeIndex> = HashMap::new();

    // 1. Create a node per model
    for model in models {
        let idx = graph.add_node(model.name.clone());
        node_map.insert(model.name.clone(), idx);
    }

    // 2. Create edges (dependency → dependent)
    for model in models {
        if let Some(&dependent_idx) = node_map.get(&model.name) {
            for ref_name in &model.refs {
                if let Some(&dependency_idx) = node_map.get(ref_name) {
                    graph.add_edge(dependency_idx, dependent_idx, ());
                }
                // Missing refs are handled by validator.rs
            }
        }
    }

    DagHandle { graph, node_map }
}

/// Return all edges as (parent_name, child_name) tuples
pub fn edges(dag: &DagHandle) -> Vec<(String, String)> {
    dag.graph
        .edge_references()
        .map(|edge| {
            let source_node = &dag.graph[edge.source()];
            let target_node = &dag.graph[edge.target()];
            (source_node.clone(), target_node.clone())
        })
        .collect()
}

#[cfg(test)]
#[path = "builder_tests.rs"]
mod tests;
