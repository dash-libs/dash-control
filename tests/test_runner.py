"""Tests for QueryResult (no Spark required — tests the wrapper, not the query)."""
from dashcontrol.runner import QueryResult


def test_query_result_ok():
    rows = [{"user": "alice", "count": 5}]
    r = QueryResult(rows, "SELECT 1")
    assert r.ok is True
    assert r.error is None
    assert len(r) == 1


def test_query_result_error():
    r = QueryResult([], "SELECT 1", error="Table not found")
    assert r.ok is False
    assert r.error == "Table not found"
    assert len(r) == 0


def test_column_names():
    rows = [{"a": 1, "b": 2}]
    r = QueryResult(rows, "")
    assert r.column_names() == ["a", "b"]


def test_column_names_empty():
    r = QueryResult([], "")
    assert r.column_names() == []


def test_column_values():
    rows = [{"user": "alice"}, {"user": "bob"}]
    r = QueryResult(rows, "")
    assert r.column_values("user") == ["alice", "bob"]


def test_first_value():
    rows = [{"dbu": 42.5}]
    r = QueryResult(rows, "")
    assert r.first_value("dbu") == 42.5


def test_first_value_default_on_empty():
    r = QueryResult([], "")
    assert r.first_value("x", default=0) == 0


def test_first_value_missing_col():
    rows = [{"a": 1}]
    r = QueryResult(rows, "")
    assert r.first_value("b", default="?") == "?"


def test_to_csv_basic():
    rows = [{"name": "alice", "count": 3}, {"name": "bob", "count": 7}]
    r = QueryResult(rows, "")
    csv = r.to_csv()
    assert "name,count" in csv
    assert "alice" in csv
    assert "bob" in csv


def test_to_csv_empty():
    r = QueryResult([], "")
    assert r.to_csv() == ""


def test_to_csv_none_values():
    rows = [{"col": None}]
    r = QueryResult(rows, "")
    csv = r.to_csv()
    assert "col" in csv
    assert "None" in csv
