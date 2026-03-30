use pyo3::prelude::*;

use crate::errors::QraftError;

/// A macro call found in SQL text
#[pyclass(frozen)]
#[derive(Clone, Debug, PartialEq)]
pub struct MacroCall {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub args: Vec<String>,
    #[pyo3(get)]
    pub start: usize,
    #[pyo3(get)]
    pub end: usize,
}

/// Find all macro calls in SQL matching the known function names.
/// Returns calls in order of appearance.
pub fn find_macro_calls(sql: &str, known_functions: &[String]) -> Result<Vec<MacroCall>, QraftError> {
    let bytes = sql.as_bytes();
    let len = bytes.len();
    let mut results = Vec::new();
    let mut i = 0;

    while i < len {
        // Skip string literals
        if bytes[i] == b'\'' {
            i = skip_single_quoted(bytes, i);
            continue;
        }
        if bytes[i] == b'"' {
            i = skip_double_quoted(bytes, i);
            continue;
        }

        // Try to match an identifier at this position
        if is_ident_start(bytes[i]) {
            let ident_start = i;
            let ident_end = scan_ident(bytes, i);
            let ident = &sql[ident_start..ident_end];

            // Boundary check: character before must NOT be alphanumeric, _, or .
            if ident_start > 0 {
                let prev = bytes[ident_start - 1];
                if prev.is_ascii_alphanumeric() || prev == b'_' || prev == b'.' {
                    i = ident_end;
                    continue;
                }
            }

            // Check if this identifier is a known function
            if known_functions.iter().any(|f| f == ident) {
                // Look for '(' after optional whitespace
                let mut j = ident_end;
                while j < len && bytes[j].is_ascii_whitespace() {
                    j += 1;
                }
                if j < len && bytes[j] == b'(' {
                    // Parse arguments
                    let args_start = j + 1; // after '('
                    match parse_args(sql, bytes, args_start) {
                        Ok((args, close_paren)) => {
                            results.push(MacroCall {
                                name: ident.to_string(),
                                args,
                                start: ident_start,
                                end: close_paren + 1, // after ')'
                            });
                            i = close_paren + 1;
                            continue;
                        }
                        Err(e) => return Err(e),
                    }
                }
            }

            i = ident_end;
            continue;
        }

        i += 1;
    }

    Ok(results)
}

fn is_ident_start(b: u8) -> bool {
    b.is_ascii_alphabetic() || b == b'_'
}

fn scan_ident(bytes: &[u8], start: usize) -> usize {
    let mut i = start;
    while i < bytes.len() && (bytes[i].is_ascii_alphanumeric() || bytes[i] == b'_') {
        i += 1;
    }
    i
}

fn skip_single_quoted(bytes: &[u8], start: usize) -> usize {
    let mut i = start + 1;
    while i < bytes.len() {
        if bytes[i] == b'\'' {
            // Check for escaped quote ''
            if i + 1 < bytes.len() && bytes[i + 1] == b'\'' {
                i += 2;
                continue;
            }
            return i + 1;
        }
        i += 1;
    }
    bytes.len()
}

fn skip_double_quoted(bytes: &[u8], start: usize) -> usize {
    let mut i = start + 1;
    while i < bytes.len() {
        if bytes[i] == b'"' {
            // Check for escaped quote ""
            if i + 1 < bytes.len() && bytes[i + 1] == b'"' {
                i += 2;
                continue;
            }
            return i + 1;
        }
        i += 1;
    }
    bytes.len()
}

/// Parse comma-separated arguments inside balanced parentheses.
/// `start` is the position right after the opening '('.
/// Returns (args, position_of_closing_paren).
fn parse_args(sql: &str, bytes: &[u8], start: usize) -> Result<(Vec<String>, usize), QraftError> {
    let len = bytes.len();
    let mut depth = 1;
    let mut i = start;
    let mut arg_start = start;
    let mut args = Vec::new();

    while i < len {
        match bytes[i] {
            b'(' => {
                depth += 1;
                i += 1;
            }
            b')' => {
                depth -= 1;
                if depth == 0 {
                    // Collect last argument
                    let arg = sql[arg_start..i].trim();
                    if !arg.is_empty() || !args.is_empty() {
                        // Only add if there's content or we already have args
                        if !arg.is_empty() {
                            args.push(arg.to_string());
                        }
                    }
                    return Ok((args, i));
                }
                i += 1;
            }
            b',' if depth == 1 => {
                let arg = sql[arg_start..i].trim().to_string();
                args.push(arg);
                arg_start = i + 1;
                i += 1;
            }
            b'\'' => {
                i = skip_single_quoted(bytes, i);
            }
            b'"' => {
                i = skip_double_quoted(bytes, i);
            }
            _ => {
                i += 1;
            }
        }
    }

    // If we get here, we never found the closing paren
    // Find the function name for error reporting
    let name_end = if start >= 1 { start - 1 } else { 0 };
    let mut name_start = name_end;
    while name_start > 0 && (bytes[name_start - 1].is_ascii_alphanumeric() || bytes[name_start - 1] == b'_') {
        name_start -= 1;
    }
    let name = sql[name_start..name_end].trim();

    Err(QraftError::UnclosedMacroCall {
        name: name.to_string(),
        position: start,
    })
}

#[cfg(test)]
#[path = "macro_parser_tests.rs"]
mod tests;
