use super::*;

fn known(names: &[&str]) -> Vec<String> {
    names.iter().map(|s| s.to_string()).collect()
}

// ── Basic cases ──

#[test]
fn test_basic_two_args() {
    let calls = find_macro_calls("SELECT safe_divide(a, b)", &known(&["safe_divide"])).unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].name, "safe_divide");
    assert_eq!(calls[0].args, vec!["a", "b"]);
}

#[test]
fn test_nested_parens() {
    let calls = find_macro_calls("SELECT safe_divide(SUM(a), COUNT(*))", &known(&["safe_divide"])).unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].args, vec!["SUM(a)", "COUNT(*)"]);
}

#[test]
fn test_string_with_comma() {
    let calls = find_macro_calls("SELECT f('hello, world', b)", &known(&["f"])).unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].args, vec!["'hello, world'", "b"]);
}

#[test]
fn test_zero_args() {
    let calls = find_macro_calls("SELECT f()", &known(&["f"])).unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].args, Vec::<String>::new());
}

#[test]
fn test_single_arg() {
    let calls = find_macro_calls("SELECT f(a)", &known(&["f"])).unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].args, vec!["a"]);
}

#[test]
fn test_whitespace_trimmed() {
    let calls = find_macro_calls("SELECT f( a , b )", &known(&["f"])).unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].args, vec!["a", "b"]);
}

// ── Boundary checks ──

#[test]
fn test_matches_known_function() {
    let calls = find_macro_calls("SELECT safe_divide(a, b)", &known(&["safe_divide"])).unwrap();
    assert_eq!(calls.len(), 1);
}

#[test]
fn test_no_match_substring() {
    let calls = find_macro_calls("SELECT my_safe_divide(a, b)", &known(&["safe_divide"])).unwrap();
    assert_eq!(calls.len(), 0);
}

#[test]
fn test_no_match_dot_prefix() {
    let calls = find_macro_calls("SELECT schema.safe_divide(a, b)", &known(&["safe_divide"])).unwrap();
    assert_eq!(calls.len(), 0);
}

#[test]
fn test_no_match_unknown() {
    let calls = find_macro_calls("SELECT COUNT(*)", &known(&["safe_divide"])).unwrap();
    assert_eq!(calls.len(), 0);
}

#[test]
fn test_match_underscore_prefix() {
    let calls = find_macro_calls("SELECT _private(a)", &known(&["_private"])).unwrap();
    assert_eq!(calls.len(), 1);
}

// ── Multiple calls ──

#[test]
fn test_multiple_calls() {
    let calls = find_macro_calls("SELECT f(a) + g(b)", &known(&["f", "g"])).unwrap();
    assert_eq!(calls.len(), 2);
    assert_eq!(calls[0].name, "f");
    assert_eq!(calls[1].name, "g");
}

#[test]
fn test_nested_call_only_outer() {
    let calls = find_macro_calls("SELECT f(g(x), y)", &known(&["f"])).unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].name, "f");
    assert_eq!(calls[0].args, vec!["g(x)", "y"]);
}

// ── String literals ──

#[test]
fn test_string_with_parens() {
    let calls = find_macro_calls("SELECT f('a(b)', c)", &known(&["f"])).unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].args, vec!["'a(b)'", "c"]);
}

#[test]
fn test_escaped_single_quote() {
    let calls = find_macro_calls("SELECT f('it''s', b)", &known(&["f"])).unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].args, vec!["'it''s'", "b"]);
}

#[test]
fn test_double_quoted_arg() {
    let calls = find_macro_calls(r#"SELECT f("col", b)"#, &known(&["f"])).unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].args, vec!["\"col\"", "b"]);
}

// ── No match ──

#[test]
fn test_no_calls_plain_sql() {
    let calls = find_macro_calls("SELECT 1", &known(&["safe_divide"])).unwrap();
    assert_eq!(calls.len(), 0);
}

#[test]
fn test_no_calls_unknown_function() {
    let calls = find_macro_calls("SELECT unknown(a)", &known(&["safe_divide"])).unwrap();
    assert_eq!(calls.len(), 0);
}

// ── Position tracking ──

#[test]
fn test_positions() {
    let sql = "SELECT safe_divide(a, b) FROM t";
    let calls = find_macro_calls(sql, &known(&["safe_divide"])).unwrap();
    assert_eq!(calls[0].start, 7);
    assert_eq!(calls[0].end, 24);
    assert_eq!(&sql[calls[0].start..calls[0].end], "safe_divide(a, b)");
}

// ── Unclosed parenthesis ──

#[test]
fn test_unclosed_paren_error() {
    let result = find_macro_calls("SELECT f(a, b", &known(&["f"]));
    assert!(result.is_err());
}

// ── Edge cases ──

#[test]
fn test_name_without_paren_not_matched() {
    let calls = find_macro_calls("SELECT safe_divide + 1", &known(&["safe_divide"])).unwrap();
    assert_eq!(calls.len(), 0);
}

#[test]
fn test_function_inside_string_not_matched() {
    let calls = find_macro_calls("SELECT 'safe_divide(a, b)'", &known(&["safe_divide"])).unwrap();
    assert_eq!(calls.len(), 0);
}
