pub mod compiler;
pub mod dag;
pub mod errors;
pub mod types;

use pyo3::prelude::*;
use std::collections::HashMap;

use compiler::macro_parser::MacroCall;
use types::*;

/// Parse a raw SQL file
#[pyfunction]
fn parse_sql(raw_sql: &str) -> PyResult<ParsedSQL> {
    Ok(compiler::parser::parse(raw_sql))
}

/// Compile a model: resolve ref(), source(), {{ var }} and generate DDL
#[pyfunction]
#[pyo3(signature = (raw_sql, model_name, schema, materialization, vars, sources, ephemerals=HashMap::new()))]
fn compile_model(
    raw_sql: &str,
    model_name: &str,
    schema: &str,
    materialization: &str,
    vars: HashMap<String, String>,
    sources: HashMap<String, SourceInfo>,
    ephemerals: HashMap<String, EphemeralModel>,
) -> PyResult<CompiledModel> {
    let parsed = compiler::parser::parse(raw_sql);

    // Front-matter materialization overrides the env default
    let effective_materialization = parsed
        .front_matter
        .as_ref()
        .and_then(|fm| fm.get("materialization"))
        .map(|s| s.as_str())
        .unwrap_or(materialization);

    let result = compiler::resolver::resolve(
        raw_sql,
        &parsed.body,
        model_name,
        schema,
        effective_materialization,
        &vars,
        &sources,
        &parsed.refs,
        &parsed.sources,
        &parsed.front_matter,
        &ephemerals,
    )?;
    Ok(result)
}

/// Phase 1 of two-phase compilation: resolve refs, sources, vars — no DDL
#[pyfunction]
#[pyo3(signature = (raw_sql, model_name, schema, materialization, vars, sources, ephemerals=HashMap::new()))]
fn resolve_model(
    raw_sql: &str,
    model_name: &str,
    schema: &str,
    materialization: &str,
    vars: HashMap<String, String>,
    sources: HashMap<String, SourceInfo>,
    ephemerals: HashMap<String, EphemeralModel>,
) -> PyResult<ResolvedModel> {
    let parsed = compiler::parser::parse(raw_sql);

    let effective_materialization = parsed
        .front_matter
        .as_ref()
        .and_then(|fm| fm.get("materialization"))
        .map(|s| s.as_str())
        .unwrap_or(materialization);

    let result = compiler::resolver::resolve_sql(
        &parsed.body,
        model_name,
        schema,
        effective_materialization,
        &vars,
        &sources,
        &parsed.refs,
        &parsed.sources,
        &parsed.front_matter,
        &ephemerals,
    )?;
    Ok(result)
}

/// Phase 2 of two-phase compilation: wrap resolved SQL in DDL
/// If resolved_sql is provided, it overrides the SQL from the ResolvedModel
/// (used when macros have modified the SQL).
#[pyfunction]
#[pyo3(signature = (resolved, resolved_sql=None))]
fn wrap_ddl(resolved: &ResolvedModel, resolved_sql: Option<String>) -> PyResult<CompiledModel> {
    match resolved_sql {
        Some(sql) => {
            let mut patched = resolved.clone();
            patched.resolved_sql = sql;
            let result = compiler::resolver::wrap_ddl(&patched)?;
            Ok(result)
        }
        None => {
            let result = compiler::resolver::wrap_ddl(resolved)?;
            Ok(result)
        }
    }
}

/// Find macro calls in SQL text matching known function names
#[pyfunction]
fn find_macro_calls(sql: &str, known_functions: Vec<String>) -> PyResult<Vec<MacroCall>> {
    let result = compiler::macro_parser::find_macro_calls(sql, &known_functions)?;
    Ok(result)
}

/// Build a DAG from a list of parsed models
#[pyfunction]
fn build_dag(models: Vec<ParsedModel>) -> PyResult<DagHandle> {
    Ok(dag::builder::build(&models))
}

/// Validate the DAG: cycles, missing refs, undeclared sources
#[pyfunction]
fn validate_dag(
    dag: &DagHandle,
    models: Vec<ParsedModel>,
    available_sources: Vec<String>,
) -> PyResult<Vec<ValidationError>> {
    Ok(dag::validator::validate(dag, &models, &available_sources))
}

/// Topological sort → parallel execution batches
#[pyfunction]
fn topo_sort(dag: &DagHandle) -> PyResult<Vec<Vec<String>>> {
    Ok(dag::sorter::topo_sort_batches(dag))
}

/// Return all DAG edges as (parent, child) tuples
#[pyfunction]
fn dag_edges(dag: &DagHandle) -> PyResult<Vec<(String, String)>> {
    Ok(dag::builder::edges(dag))
}

/// Consolidated DAG pipeline: parse → build → validate → sort (→ select) in one call.
/// Takes raw SQL strings and returns (DagHandle, batches, parsed_models, errors).
/// If `select` is provided, batches are filtered to only include selected models.
#[pyfunction]
#[pyo3(signature = (raw_models, available_sources, select=None))]
fn build_pipeline(
    raw_models: Vec<(String, String)>,
    available_sources: Vec<String>,
    select: Option<String>,
) -> PyResult<(DagHandle, Vec<Vec<String>>, Vec<ParsedModel>, Vec<ValidationError>)> {
    let models: Vec<dag::pipeline::RawModel> = raw_models
        .into_iter()
        .map(|(name, raw_sql)| dag::pipeline::RawModel { name, raw_sql })
        .collect();
    let (dag, batches, parsed_models, errors) =
        dag::pipeline::build_pipeline(&models, &available_sources, select.as_deref());
    Ok((dag, batches, parsed_models, errors))
}

/// Batch resolve: parse + resolve all models in one call.
/// Input: list of (name, raw_sql) tuples + env config.
/// Returns list of ResolvedModel.
#[pyfunction]
#[pyo3(signature = (raw_models, schema, materialization, vars, sources, ephemerals=HashMap::new()))]
fn batch_resolve(
    raw_models: Vec<(String, String)>,
    schema: &str,
    materialization: &str,
    vars: HashMap<String, String>,
    sources: HashMap<String, SourceInfo>,
    ephemerals: HashMap<String, EphemeralModel>,
) -> PyResult<Vec<ResolvedModel>> {
    let models: Vec<compiler::batch::RawModelInput> = raw_models
        .into_iter()
        .map(|(name, raw_sql)| compiler::batch::RawModelInput { name, raw_sql })
        .collect();
    let results = compiler::batch::batch_resolve(
        &models, schema, materialization, &vars, &sources, &ephemerals,
    )?;
    Ok(results)
}

/// Batch wrap DDL: wrap all resolved models in DDL in one call.
#[pyfunction]
fn batch_wrap_ddl(models: Vec<ResolvedModel>) -> PyResult<Vec<CompiledModel>> {
    let results = compiler::batch::batch_wrap_ddl(&models)?;
    Ok(results)
}

/// Select models by pattern
#[pyfunction]
#[pyo3(signature = (dag, pattern, tags_map=HashMap::new()))]
fn select_models(
    dag: &DagHandle,
    pattern: &str,
    tags_map: HashMap<String, Vec<String>>,
) -> PyResult<Vec<String>> {
    Ok(dag::selector::select(dag, pattern, &tags_map))
}

/// Python module: qraft._core
#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Functions
    m.add_function(wrap_pyfunction!(parse_sql, m)?)?;
    m.add_function(wrap_pyfunction!(compile_model, m)?)?;
    m.add_function(wrap_pyfunction!(resolve_model, m)?)?;
    m.add_function(wrap_pyfunction!(wrap_ddl, m)?)?;
    m.add_function(wrap_pyfunction!(find_macro_calls, m)?)?;
    m.add_function(wrap_pyfunction!(build_dag, m)?)?;
    m.add_function(wrap_pyfunction!(validate_dag, m)?)?;
    m.add_function(wrap_pyfunction!(topo_sort, m)?)?;
    m.add_function(wrap_pyfunction!(dag_edges, m)?)?;
    m.add_function(wrap_pyfunction!(build_pipeline, m)?)?;
    m.add_function(wrap_pyfunction!(batch_resolve, m)?)?;
    m.add_function(wrap_pyfunction!(batch_wrap_ddl, m)?)?;
    m.add_function(wrap_pyfunction!(select_models, m)?)?;

    // Classes
    m.add_class::<ParsedSQL>()?;
    m.add_class::<CompiledModel>()?;
    m.add_class::<ResolvedModel>()?;
    m.add_class::<MacroCall>()?;
    m.add_class::<SourceInfo>()?;
    m.add_class::<ParsedModel>()?;
    m.add_class::<EphemeralModel>()?;
    m.add_class::<DagHandle>()?;
    m.add_class::<ValidationError>()?;

    Ok(())
}
