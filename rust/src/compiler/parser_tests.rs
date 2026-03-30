use super::*;

#[test]
fn test_parse_refs() {
    let sql = "SELECT * FROM ref('stg_orders') o JOIN ref('stg_customers') c ON o.id = c.id";
    let parsed = parse(sql);
    assert_eq!(parsed.refs, vec!["stg_orders", "stg_customers"]);
}

#[test]
fn test_parse_sources() {
    let sql = "SELECT * FROM source('raw_data', 'orders')";
    let parsed = parse(sql);
    assert_eq!(
        parsed.sources,
        vec![("raw_data".into(), "orders".into())]
    );
}

#[test]
fn test_parse_variables() {
    let sql = "SELECT * FROM {{ schema }}.table WHERE amount > {{ min_amount }}";
    let parsed = parse(sql);
    assert_eq!(parsed.variables, vec!["schema", "min_amount"]);
}

#[test]
fn test_front_matter() {
    let sql = "---\nmaterialization: table\n---\nSELECT 1";
    let parsed = parse(sql);
    assert_eq!(
        parsed
            .front_matter
            .unwrap()
            .get("materialization")
            .unwrap(),
        "table"
    );
}

#[test]
fn test_no_front_matter() {
    let sql = "SELECT 1";
    let parsed = parse(sql);
    assert!(parsed.front_matter.is_none());
    assert_eq!(parsed.body, "SELECT 1");
}

#[test]
fn test_double_quotes() {
    let sql = r#"SELECT * FROM ref("stg_orders") JOIN source("raw", "orders")"#;
    let parsed = parse(sql);
    assert_eq!(parsed.refs, vec!["stg_orders"]);
    assert_eq!(parsed.sources, vec![("raw".into(), "orders".into())]);
}

#[test]
fn test_front_matter_tags_brackets() {
    let sql = "---\ntags: [staging, daily]\n---\nSELECT 1";
    let parsed = parse(sql);
    let fm = parsed.front_matter.unwrap();
    assert_eq!(fm.get("tags").unwrap(), "staging,daily");
}

#[test]
fn test_front_matter_description() {
    let sql = "---\ndescription: \"Customer lifetime value\"\nmaterialization: table\n---\nSELECT 1";
    let parsed = parse(sql);
    let fm = parsed.front_matter.unwrap();
    assert_eq!(fm.get("description").unwrap(), "Customer lifetime value");
    assert_eq!(fm.get("materialization").unwrap(), "table");
}

#[test]
fn test_front_matter_enabled_false() {
    let sql = "---\nenabled: false\n---\nSELECT 1";
    let parsed = parse(sql);
    let fm = parsed.front_matter.unwrap();
    assert_eq!(fm.get("enabled").unwrap(), "false");
}

#[test]
fn test_front_matter_schema_override() {
    let sql = "---\nschema: custom_schema\nmaterialization: view\n---\nSELECT 1";
    let parsed = parse(sql);
    let fm = parsed.front_matter.unwrap();
    assert_eq!(fm.get("schema").unwrap(), "custom_schema");
}
