use std::collections::{HashMap, HashSet};

use crate::compiler::parser;
use crate::types::{DagHandle, ParsedModel, ValidationError};

use super::builder;
use super::selector;
use super::sorter;
use super::validator;

/// Raw model input: just a name and SQL string
pub struct RawModel {
    pub name: String,
    pub raw_sql: String,
}

/// Consolidated DAG pipeline: parse → build → validate → sort (→ select) in one call.
/// Returns (dag, batches, parsed_models, errors).
/// If `select` is provided, batches are filtered to only include selected models.
pub fn build_pipeline(
    raw_models: &[RawModel],
    available_sources: &[String],
    select: Option<&str>,
) -> (DagHandle, Vec<Vec<String>>, Vec<ParsedModel>, Vec<ValidationError>) {
    // 1. Parse all SQL files → ParsedModel
    let parsed_models: Vec<ParsedModel> = raw_models
        .iter()
        .map(|raw_model| {
            let parsed = parser::parse(&raw_model.raw_sql);
            let tags = parsed
                .front_matter
                .as_ref()
                .and_then(|fm| fm.get("tags"))
                .map(|tags_str| tags_str.split(',').map(|item| item.trim().to_string()).collect())
                .unwrap_or_default();
            let materialization = parsed
                .front_matter
                .as_ref()
                .and_then(|fm| fm.get("materialization"))
                .cloned();
            ParsedModel {
                name: raw_model.name.clone(),
                refs: parsed.refs,
                sources: parsed.sources,
                tags,
                materialization,
            }
        })
        .collect();

    // 2. Build DAG
    let dag = builder::build(&parsed_models);

    // 3. Validate
    let errors = validator::validate(&dag, &parsed_models, available_sources);

    // 4. Topological sort
    let batches = sorter::topo_sort_batches(&dag);

    // 5. Apply selection filter (optional)
    let batches = if let Some(pattern) = select {
        let tags_map: HashMap<String, Vec<String>> = parsed_models
            .iter()
            .filter(|parsed_model| !parsed_model.tags.is_empty())
            .map(|parsed_model| (parsed_model.name.clone(), parsed_model.tags.clone()))
            .collect();
        let selected: HashSet<String> = selector::select(&dag, pattern, &tags_map)
            .into_iter()
            .collect();
        batches
            .into_iter()
            .map(|batch| {
                batch
                    .into_iter()
                    .filter(|name| selected.contains(name))
                    .collect::<Vec<_>>()
            })
            .filter(|batch| !batch.is_empty())
            .collect()
    } else {
        batches
    };

    (dag, batches, parsed_models, errors)
}

#[cfg(test)]
#[path = "pipeline_tests.rs"]
mod tests;
