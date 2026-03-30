use pyo3::exceptions::PyValueError;
use pyo3::PyErr;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum QraftError {
    #[error("Unresolved variable: {{{{ {name} }}}}")]
    UnresolvedVariable { name: String },

    #[error("Unknown ref: ref('{name}') in model '{model}'")]
    UnknownRef { model: String, name: String },

    #[error("Unknown source: source('{source_name}', '{table}') in model '{model}'")]
    UnknownSource {
        model: String,
        source_name: String,
        table: String,
    },

    #[error("Circular dependency detected: {path}")]
    CyclicDependency { path: String },

    #[error("Invalid select pattern: '{pattern}'")]
    InvalidPattern { pattern: String },

    #[error("Invalid materialization: '{materialization}' in model '{model}'")]
    InvalidMaterialization {
        model: String,
        materialization: String,
    },

    #[error("Unclosed parenthesis in macro call '{name}' at position {position}")]
    UnclosedMacroCall { name: String, position: usize },

    #[error("Unclosed string literal in macro call '{name}' at position {position}")]
    UnclosedStringInMacro { name: String, position: usize },
}

impl From<QraftError> for PyErr {
    fn from(err: QraftError) -> PyErr {
        PyValueError::new_err(err.to_string())
    }
}
