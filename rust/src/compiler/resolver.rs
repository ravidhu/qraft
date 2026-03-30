use std::collections::{HashMap, HashSet};

use crate::errors::QraftError;
use crate::types::{CompiledModel, EphemeralModel, ResolvedModel, SourceInfo};

/// Resolve a parsed model's SQL: refs, sources, vars, ephemeral CTEs.
/// Returns a ResolvedModel with resolved SQL but no DDL wrapping.
pub fn resolve_sql(
    body: &str,
    model_name: &str,
    schema: &str,
    materialization: &str,
    vars: &HashMap<String, String>,
    sources: &HashMap<String, SourceInfo>,
    refs: &[String],
    source_refs: &[(String, String)],
    front_matter: &Option<HashMap<String, String>>,
    ephemerals: &HashMap<String, EphemeralModel>,
) -> Result<ResolvedModel, QraftError> {
    let mut sql = body.to_string();

    // Extract extended front-matter fields
    let description = front_matter
        .as_ref()
        .and_then(|fm| fm.get("description"))
        .cloned();
    let tags: Vec<String> = front_matter
        .as_ref()
        .and_then(|fm| fm.get("tags"))
        .map(|tags_str| tags_str.split(',').map(|item| item.trim().to_string()).filter(|item| !item.is_empty()).collect())
        .unwrap_or_default();
    let enabled = front_matter
        .as_ref()
        .and_then(|fm| fm.get("enabled"))
        .map(|v| v != "false")
        .unwrap_or(true);
    let effective_schema = front_matter
        .as_ref()
        .and_then(|fm| fm.get("schema"))
        .map(|schema_str| schema_str.as_str())
        .unwrap_or(schema);
    let macros: Vec<String> = front_matter
        .as_ref()
        .and_then(|fm| fm.get("macros"))
        .map(|macros_str| macros_str.split(',').map(|item| item.trim().to_string()).filter(|item| !item.is_empty()).collect())
        .unwrap_or_default();
    let unique_key = front_matter
        .as_ref()
        .and_then(|fm| fm.get("unique_key"))
        .cloned();

    // 1. Partition refs into ephemeral and regular
    let (ephemeral_refs, regular_refs): (Vec<&String>, Vec<&String>) =
        refs.iter().partition(|r| ephemerals.contains_key(*r));

    // 2. Resolve regular ref() -> schema.model_name
    //    Use the env default schema (not per-model override) since refs target
    //    other models which live in the default schema unless they have their own override.
    for ref_name in &regular_refs {
        let replacement = format!("{schema}.{ref_name}");
        let pattern = format!("ref('{ref_name}')");
        sql = sql.replace(&pattern, &replacement);
        let pattern_dq = format!("ref(\"{ref_name}\")");
        sql = sql.replace(&pattern_dq, &replacement);
    }

    // 3. Resolve ephemeral ref() -> just the CTE alias (no schema prefix)
    for ref_name in &ephemeral_refs {
        let replacement = ref_name.to_string();
        let pattern = format!("ref('{ref_name}')");
        sql = sql.replace(&pattern, &replacement);
        let pattern_dq = format!("ref(\"{ref_name}\")");
        sql = sql.replace(&pattern_dq, &replacement);
    }

    // 4. Resolve source() -> database.schema.table
    for (source_name, table_name) in source_refs {
        let info = sources.get(source_name).ok_or_else(|| QraftError::UnknownSource {
            model: model_name.to_string(),
            source_name: source_name.clone(),
            table: table_name.clone(),
        })?;

        let qualified = if info.database.is_empty() {
            format!("{}.{}", info.schema, table_name)
        } else {
            format!("{}.{}.{}", info.database, info.schema, table_name)
        };

        let pattern = format!("source('{source_name}', '{table_name}')");
        sql = sql.replace(&pattern, &qualified);
        let pattern_dq = format!("source(\"{source_name}\", \"{table_name}\")");
        sql = sql.replace(&pattern_dq, &qualified);
    }

    // 5. Resolve {{ var }}
    let mut all_vars = vars.clone();
    all_vars
        .entry("schema".to_string())
        .or_insert_with(|| effective_schema.to_string());

    let max_var_passes: usize = std::env::var("QRAFT_MAX_VAR_PASSES")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(10);

    for _ in 0..max_var_passes {
        let prev = sql.clone();
        for (key, value) in &all_vars {
            let pattern = format!("{{{{ {key} }}}}");
            sql = sql.replace(&pattern, value);
            let pattern_compact = format!("{{{{{key}}}}}");
            sql = sql.replace(&pattern_compact, value);
        }
        if sql == prev {
            break;
        }
    }

    // 6. Check for unresolved {{ variable }}
    if let Some(cap) = regex::Regex::new(r"\{\{\s*(\w+)\s*\}\}")
        .unwrap()
        .captures(&sql)
    {
        return Err(QraftError::UnresolvedVariable {
            name: cap[1].to_string(),
        });
    }

    // 7. Inject ephemeral CTEs
    if !ephemeral_refs.is_empty() {
        let ctes = collect_ephemeral_ctes(&ephemeral_refs, ephemerals);
        if !ctes.is_empty() {
            let cte_clauses: Vec<String> = ctes
                .iter()
                .map(|(name, body)| format!("{name} AS (\n{body}\n)"))
                .collect();
            let cte_str = cte_clauses.join(",\n");

            // Merge with existing WITH clause if present
            let trimmed = sql.trim_start();
            if trimmed.len() >= 5
                && trimmed[..5].eq_ignore_ascii_case("WITH ")
            {
                let rest = &trimmed[5..];
                sql = format!("WITH {cte_str},\n{rest}");
            } else {
                sql = format!("WITH {cte_str}\n{sql}");
            }
        }
    }

    let target = format!("{effective_schema}.{model_name}");

    Ok(ResolvedModel {
        name: model_name.to_string(),
        resolved_sql: sql,
        target,
        materialization: materialization.to_string(),
        refs: refs.to_vec(),
        sources: source_refs.to_vec(),
        macros,
        description,
        tags,
        enabled,
        unique_key,
    })
}

/// Wrap resolved SQL in DDL (CREATE VIEW/TABLE/etc.)
pub fn wrap_ddl(resolved: &ResolvedModel) -> Result<CompiledModel, QraftError> {
    let sql = &resolved.resolved_sql;
    let target = &resolved.target;
    let materialization = resolved.materialization.as_str();

    let ddl = match materialization {
        "view" => format!("CREATE OR REPLACE VIEW {target} AS\n{sql}"),
        "table" => format!("DROP TABLE IF EXISTS {target};\nCREATE TABLE {target} AS\n{sql}"),
        "ephemeral" => String::new(),
        "materialized_view" => {
            format!("CREATE MATERIALIZED VIEW IF NOT EXISTS {target} AS\n{sql}")
        }
        "table_incremental" => {
            if let Some(key) = &resolved.unique_key {
                format!(
                    "DELETE FROM {target} WHERE {key} IN (SELECT {key} FROM ({sql}));\n\
                     INSERT INTO {target}\n{sql}"
                )
            } else {
                format!("INSERT INTO {target}\n{sql}")
            }
        }
        other => {
            return Err(QraftError::InvalidMaterialization {
                model: resolved.name.clone(),
                materialization: other.to_string(),
            });
        }
    };

    Ok(CompiledModel {
        name: resolved.name.clone(),
        compiled_sql: resolved.resolved_sql.clone(),
        ddl,
        target: resolved.target.clone(),
        materialization: resolved.materialization.clone(),
        refs: resolved.refs.clone(),
        sources: resolved.sources.clone(),
        description: resolved.description.clone(),
        tags: resolved.tags.clone(),
        enabled: resolved.enabled,
    })
}

/// Original resolve function — thin wrapper calling resolve_sql + wrap_ddl
pub fn resolve(
    _raw_sql: &str,
    body: &str,
    model_name: &str,
    schema: &str,
    materialization: &str,
    vars: &HashMap<String, String>,
    sources: &HashMap<String, SourceInfo>,
    refs: &[String],
    source_refs: &[(String, String)],
    front_matter: &Option<HashMap<String, String>>,
    ephemerals: &HashMap<String, EphemeralModel>,
) -> Result<CompiledModel, QraftError> {
    let resolved = resolve_sql(
        body, model_name, schema, materialization,
        vars, sources, refs, source_refs,
        front_matter, ephemerals,
    )?;
    wrap_ddl(&resolved)
}

/// Collect all transitive ephemeral CTEs in dependency order (DFS)
fn collect_ephemeral_ctes(
    direct_refs: &[&String],
    ephemerals: &HashMap<String, EphemeralModel>,
) -> Vec<(String, String)> {
    let mut visited = HashSet::new();
    let mut order = Vec::new();

    for ref_name in direct_refs {
        collect_recursive(ref_name, ephemerals, &mut visited, &mut order);
    }

    order
}

fn collect_recursive(
    name: &str,
    ephemerals: &HashMap<String, EphemeralModel>,
    visited: &mut HashSet<String>,
    order: &mut Vec<(String, String)>,
) {
    if visited.contains(name) {
        return;
    }
    visited.insert(name.to_string());

    if let Some(eph) = ephemerals.get(name) {
        // Recurse into this ephemeral's own deps first
        for dep in &eph.deps {
            collect_recursive(dep, ephemerals, visited, order);
        }
        order.push((name.to_string(), eph.compiled_body.clone()));
    }
}

#[cfg(test)]
#[path = "resolver_tests.rs"]
mod tests;
