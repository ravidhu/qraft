use regex::Regex;
use std::collections::HashMap;
use std::sync::LazyLock;

use crate::types::ParsedSQL;

static REF_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"ref\(\s*['\x22](\w+)['\x22]\s*\)").unwrap());

static SOURCE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"source\(\s*['\x22](\w+)['\x22]\s*,\s*['\x22](\w+)['\x22]\s*\)").unwrap()
});

static VAR_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\{\{\s*(\w+)\s*\}\}").unwrap());

/// Parse raw SQL: extract refs, sources, variables, front-matter
pub fn parse(raw_sql: &str) -> ParsedSQL {
    let (front_matter, body) = extract_front_matter(raw_sql);

    let refs: Vec<String> = REF_RE
        .captures_iter(&body)
        .map(|c| c[1].to_string())
        .collect();

    let sources: Vec<(String, String)> = SOURCE_RE
        .captures_iter(&body)
        .map(|c| (c[1].to_string(), c[2].to_string()))
        .collect();

    let variables: Vec<String> = VAR_RE
        .captures_iter(&body)
        .map(|c| c[1].to_string())
        .collect();

    ParsedSQL {
        refs,
        sources,
        variables,
        body,
        front_matter,
    }
}

/// Extract YAML front-matter (between --- and ---) if present
fn extract_front_matter(sql: &str) -> (Option<HashMap<String, String>>, String) {
    let trimmed = sql.trim_start();
    if !trimmed.starts_with("---") {
        return (None, sql.to_string());
    }

    if let Some(end) = trimmed[3..].find("---") {
        let yaml_block = &trimmed[3..end + 3];
        let body = trimmed[end + 6..].to_string();

        // Simple YAML parse: key: value (one pair per line)
        let mut map = HashMap::new();
        for line in yaml_block.lines() {
            let line = line.trim();
            if let Some((key, value)) = line.split_once(':') {
                let key = key.trim().to_string();
                let value = value.trim();
                // Handle bracket list syntax: [a, b, c] → "a,b,c"
                let value = if value.starts_with('[') && value.ends_with(']') {
                    value[1..value.len() - 1]
                        .split(',')
                        .map(|s| s.trim().trim_matches(|c| c == '\'' || c == '"'))
                        .collect::<Vec<_>>()
                        .join(",")
                } else {
                    // Strip surrounding quotes
                    value
                        .trim_matches('"')
                        .trim_matches('\'')
                        .to_string()
                };
                map.insert(key, value);
            }
        }
        (Some(map), body)
    } else {
        (None, sql.to_string())
    }
}

#[cfg(test)]
#[path = "parser_tests.rs"]
mod tests;
