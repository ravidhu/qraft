use std::collections::HashMap;

use crate::compiler::parser;
use crate::compiler::resolver;
use crate::errors::QraftError;
use crate::types::{CompiledModel, EphemeralModel, ResolvedModel, SourceInfo};

/// Input for batch resolution: model name + raw SQL
pub struct RawModelInput {
    pub name: String,
    pub raw_sql: String,
}

/// Batch resolve: parse + resolve all models in one call.
/// Returns a list of ResolvedModel or an error if any model fails.
pub fn batch_resolve(
    models: &[RawModelInput],
    schema: &str,
    default_materialization: &str,
    vars: &HashMap<String, String>,
    sources: &HashMap<String, SourceInfo>,
    ephemerals: &HashMap<String, EphemeralModel>,
) -> Result<Vec<ResolvedModel>, QraftError> {
    let mut results = Vec::with_capacity(models.len());

    for model in models {
        let parsed = parser::parse(&model.raw_sql);

        let effective_materialization = parsed
            .front_matter
            .as_ref()
            .and_then(|fm| fm.get("materialization"))
            .map(|s| s.as_str())
            .unwrap_or(default_materialization);

        let resolved = resolver::resolve_sql(
            &parsed.body,
            &model.name,
            schema,
            effective_materialization,
            vars,
            sources,
            &parsed.refs,
            &parsed.sources,
            &parsed.front_matter,
            ephemerals,
        )?;

        results.push(resolved);
    }

    Ok(results)
}

/// Batch wrap DDL: wrap all resolved models in DDL in one call.
pub fn batch_wrap_ddl(
    models: &[ResolvedModel],
) -> Result<Vec<CompiledModel>, QraftError> {
    let mut results = Vec::with_capacity(models.len());

    for model in models {
        let compiled = resolver::wrap_ddl(model)?;
        results.push(compiled);
    }

    Ok(results)
}

#[cfg(test)]
#[path = "batch_tests.rs"]
mod tests;
