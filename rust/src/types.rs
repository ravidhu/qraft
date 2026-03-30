use pyo3::prelude::*;
use std::collections::HashMap;

// ─────────────────────────────────
// Parsing
// ─────────────────────────────────

/// Result of parsing a raw SQL file
#[pyclass(frozen)]
#[derive(Clone, Debug)]
pub struct ParsedSQL {
    #[pyo3(get)]
    pub refs: Vec<String>,
    #[pyo3(get)]
    pub sources: Vec<(String, String)>,
    #[pyo3(get)]
    pub variables: Vec<String>,
    #[pyo3(get)]
    pub body: String,
    #[pyo3(get)]
    pub front_matter: Option<HashMap<String, String>>,
}

// ─────────────────────────────────
// Compilation
// ─────────────────────────────────

/// Compiled model, ready to be executed by a Python engine
#[pyclass(frozen)]
#[derive(Clone, Debug)]
pub struct CompiledModel {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub compiled_sql: String,
    #[pyo3(get)]
    pub ddl: String,
    #[pyo3(get)]
    pub target: String,
    #[pyo3(get)]
    pub materialization: String,
    #[pyo3(get)]
    pub refs: Vec<String>,
    #[pyo3(get)]
    pub sources: Vec<(String, String)>,
    #[pyo3(get)]
    pub description: Option<String>,
    #[pyo3(get)]
    pub tags: Vec<String>,
    #[pyo3(get)]
    pub enabled: bool,
}

// ─────────────────────────────────
// Resolution (intermediate step)
// ─────────────────────────────────

/// Resolved model — after ref/var/source resolution, before DDL wrapping
#[pyclass(frozen)]
#[derive(Clone, Debug)]
pub struct ResolvedModel {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub resolved_sql: String,
    #[pyo3(get)]
    pub target: String,
    #[pyo3(get)]
    pub materialization: String,
    #[pyo3(get)]
    pub refs: Vec<String>,
    #[pyo3(get)]
    pub sources: Vec<(String, String)>,
    #[pyo3(get)]
    pub macros: Vec<String>,
    #[pyo3(get)]
    pub description: Option<String>,
    #[pyo3(get)]
    pub tags: Vec<String>,
    #[pyo3(get)]
    pub enabled: bool,
    #[pyo3(get)]
    pub unique_key: Option<String>,
}

// ─────────────────────────────────
// Source info (passed by Python)
// ─────────────────────────────────

/// Source info, passed by Python after config resolution
#[pyclass(frozen)]
#[derive(Clone, Debug)]
pub struct SourceInfo {
    #[pyo3(get)]
    pub database: String,
    #[pyo3(get)]
    pub schema: String,
}

#[pymethods]
impl SourceInfo {
    #[new]
    pub fn new(database: String, schema: String) -> Self {
        Self { database, schema }
    }
}

// ─────────────────────────────────
// DAG
// ─────────────────────────────────

/// Input for building the DAG — a minimal parsed model
#[pyclass(frozen)]
#[derive(Clone, Debug)]
pub struct ParsedModel {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub refs: Vec<String>,
    #[pyo3(get)]
    pub sources: Vec<(String, String)>,
    #[pyo3(get)]
    pub tags: Vec<String>,
    #[pyo3(get)]
    pub materialization: Option<String>,
}

#[pymethods]
impl ParsedModel {
    #[new]
    #[pyo3(signature = (name, refs, sources, tags=vec![], materialization=None))]
    pub fn new(
        name: String,
        refs: Vec<String>,
        sources: Vec<(String, String)>,
        tags: Vec<String>,
        materialization: Option<String>,
    ) -> Self {
        Self { name, refs, sources, tags, materialization }
    }
}

// ─────────────────────────────────
// Ephemeral model info
// ─────────────────────────────────

/// Info about an ephemeral model, passed to compile_model for CTE injection
#[pyclass(frozen)]
#[derive(Clone, Debug)]
pub struct EphemeralModel {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub compiled_body: String,
    #[pyo3(get)]
    pub deps: Vec<String>,
}

#[pymethods]
impl EphemeralModel {
    #[new]
    pub fn new(name: String, compiled_body: String, deps: Vec<String>) -> Self {
        Self { name, compiled_body, deps }
    }
}

/// Opaque handle to the internal DAG (petgraph stored on Rust side)
#[pyclass]
pub struct DagHandle {
    pub(crate) graph: petgraph::Graph<String, (), petgraph::Directed>,
    pub(crate) node_map: HashMap<String, petgraph::graph::NodeIndex>,
}

// ─────────────────────────────────
// Validation
// ─────────────────────────────────

#[pyclass(frozen)]
#[derive(Clone, Debug)]
pub struct ValidationError {
    #[pyo3(get)]
    pub model: String,
    #[pyo3(get)]
    pub error_type: String,
    #[pyo3(get)]
    pub message: String,
    #[pyo3(get)]
    pub suggestion: Option<String>,
}

