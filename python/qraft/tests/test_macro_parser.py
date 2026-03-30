"""Tests for _core.find_macro_calls — exercises the PyO3 boundary."""

from qraft import _core


class TestFindMacroCalls:
    def test_basic_two_args(self):
        calls = _core.find_macro_calls("SELECT safe_divide(a, b)", ["safe_divide"])
        assert len(calls) == 1
        assert calls[0].name == "safe_divide"
        assert calls[0].args == ["a", "b"]

    def test_nested_parens(self):
        calls = _core.find_macro_calls(
            "SELECT safe_divide(SUM(a), COUNT(*))", ["safe_divide"]
        )
        assert calls[0].args == ["SUM(a)", "COUNT(*)"]

    def test_string_with_comma(self):
        calls = _core.find_macro_calls("SELECT f('hello, world', b)", ["f"])
        assert calls[0].args == ["'hello, world'", "b"]

    def test_zero_args(self):
        calls = _core.find_macro_calls("SELECT f()", ["f"])
        assert len(calls) == 1
        assert calls[0].args == []

    def test_no_match_substring(self):
        calls = _core.find_macro_calls(
            "SELECT my_safe_divide(a, b)", ["safe_divide"]
        )
        assert len(calls) == 0

    def test_no_match_dot_prefix(self):
        calls = _core.find_macro_calls(
            "SELECT schema.safe_divide(a, b)", ["safe_divide"]
        )
        assert len(calls) == 0

    def test_multiple_calls(self):
        calls = _core.find_macro_calls("SELECT f(a) + g(b)", ["f", "g"])
        assert len(calls) == 2
        assert calls[0].name == "f"
        assert calls[1].name == "g"

    def test_positions(self):
        sql = "SELECT safe_divide(a, b) FROM t"
        calls = _core.find_macro_calls(sql, ["safe_divide"])
        assert sql[calls[0].start : calls[0].end] == "safe_divide(a, b)"

    def test_function_inside_string_not_matched(self):
        calls = _core.find_macro_calls(
            "SELECT 'safe_divide(a, b)'", ["safe_divide"]
        )
        assert len(calls) == 0

    def test_no_calls(self):
        calls = _core.find_macro_calls("SELECT 1", ["safe_divide"])
        assert len(calls) == 0
