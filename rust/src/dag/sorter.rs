use petgraph::visit::EdgeRef;
use petgraph::Direction;
use std::collections::VecDeque;

use crate::types::DagHandle;

/// Topological sort by levels → Vec of batches
/// Each batch contains models that can run in parallel
pub fn topo_sort_batches(dag: &DagHandle) -> Vec<Vec<String>> {
    let graph = &dag.graph;
    let mut in_degree: Vec<usize> = vec![0; graph.node_count()];
    let mut batches: Vec<Vec<String>> = Vec::new();

    // Calculate in-degree of each node
    for edge in graph.edge_references() {
        in_degree[edge.target().index()] += 1;
    }

    // Queue of nodes with in-degree = 0
    let mut queue: VecDeque<petgraph::graph::NodeIndex> = graph
        .node_indices()
        .filter(|&node| in_degree[node.index()] == 0)
        .collect();

    while !queue.is_empty() {
        // All nodes in the current queue form a batch
        let current: Vec<petgraph::graph::NodeIndex> = queue.drain(..).collect();
        let mut batch = Vec::new();

        for node in current {
            batch.push(graph[node].clone());

            // Decrement in-degree of neighbors
            let neighbors: Vec<_> = graph
                .neighbors_directed(node, Direction::Outgoing)
                .collect();
            for neighbor in neighbors {
                in_degree[neighbor.index()] -= 1;
                if in_degree[neighbor.index()] == 0 {
                    queue.push_back(neighbor);
                }
            }
        }

        if !batch.is_empty() {
            batches.push(batch);
        }
    }

    batches
}

#[cfg(test)]
#[path = "sorter_tests.rs"]
mod tests;
