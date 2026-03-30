use petgraph::algo::is_cyclic_directed;
use strsim::jaro_winkler;

use crate::types::{DagHandle, ParsedModel, ValidationError};

/// Validate the DAG: cycles, missing refs, undeclared sources
pub fn validate(
    dag: &DagHandle,
    models: &[ParsedModel],
    available_sources: &[String],
) -> Vec<ValidationError> {
    let mut errors = Vec::new();
    let model_names: Vec<&str> = models.iter().map(|model| model.name.as_str()).collect();

    // 1. Check missing refs
    for model in models {
        for ref_name in &model.refs {
            if !dag.node_map.contains_key(ref_name) {
                let suggestion = fuzzy_suggest(ref_name, &model_names, 0.8);
                errors.push(ValidationError {
                    model: model.name.clone(),
                    error_type: "missing_ref".to_string(),
                    message: format!("ref('{}') not found", ref_name),
                    suggestion,
                });
            }
        }
    }

    // 2. Check undeclared sources
    for model in models {
        for (source_name, _table_name) in &model.sources {
            if !available_sources.contains(source_name) {
                let suggestion = fuzzy_suggest(
                    source_name,
                    &available_sources
                        .iter()
                        .map(|s| s.as_str())
                        .collect::<Vec<_>>(),
                    0.8,
                );
                errors.push(ValidationError {
                    model: model.name.clone(),
                    error_type: "missing_source".to_string(),
                    message: format!(
                        "source('{}') not declared in project.yaml",
                        source_name
                    ),
                    suggestion,
                });
            }
        }
    }

    // 3. Detect cycles
    if is_cyclic_directed(&dag.graph) {
        let cycle_path = find_cycle_path(dag);
        errors.push(ValidationError {
            model: cycle_path.first().cloned().unwrap_or_default(),
            error_type: "cycle".to_string(),
            message: format!(
                "Circular dependency detected: {}",
                cycle_path.join(" → ")
            ),
            suggestion: Some(
                "Remove one of the ref() calls to break the cycle.".to_string(),
            ),
        });
    }

    errors
}

/// Fuzzy suggestion: return the best match if score exceeds threshold
fn fuzzy_suggest(input: &str, candidates: &[&str], threshold: f64) -> Option<String> {
    candidates
        .iter()
        .map(|&c| (c, jaro_winkler(input, c)))
        .filter(|(_, score)| *score >= threshold)
        .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
        .map(|(name, _)| name.to_string())
}

/// Find a cycle in the graph for display
fn find_cycle_path(dag: &DagHandle) -> Vec<String> {
    use petgraph::visit::{depth_first_search, Control, DfsEvent};

    let mut path = Vec::new();

    depth_first_search(&dag.graph, dag.graph.node_indices(), |event| {
        match event {
            DfsEvent::BackEdge(from, to) => {
                // Cycle found
                path.push(dag.graph[to].clone());
                path.push(dag.graph[from].clone());
                path.push(dag.graph[to].clone());
                Control::<()>::Break(())
            }
            _ => Control::Continue,
        }
    });

    path
}

#[cfg(test)]
#[path = "validator_tests.rs"]
mod tests;
