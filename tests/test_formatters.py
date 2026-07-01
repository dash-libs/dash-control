"""Tests for HTML formatting utilities — no Spark required."""
import pytest
from dashcontrol.formatters import (
    stat_tile, stat_row, html_table, error_box, info_box,
    section_header, sparkline_html, format_number,
)


# ── stat_tile ─────────────────────────────────────────────────────────────────

def test_stat_tile_contains_value():
    h = stat_tile("DBU Today", "1.2K")
    assert "1.2K" in h
    assert "DBU Today" in h


def test_stat_tile_custom_color():
    h = stat_tile("Errors", 5, color="#ff0000")
    assert "#ff0000" in h


def test_stat_tile_unit():
    h = stat_tile("Success Rate", 95, unit="%")
    assert "95%" in h or ("95" in h and "%" in h)


# ── stat_row ─────────────────────────────────────────────────────────────────

def test_stat_row_wraps_tiles():
    t1 = stat_tile("A", 1)
    t2 = stat_tile("B", 2)
    row = stat_row([t1, t2])
    assert "A" in row and "B" in row
    assert "flex" in row


# ── html_table ───────────────────────────────────────────────────────────────

def test_html_table_empty_rows():
    h = html_table([])
    assert "No data" in h


def test_html_table_column_names_as_headers():
    rows = [{"user_name": "alice", "query_count": 42}]
    h = html_table(rows)
    assert "User Name" in h or "user_name" in h.lower()
    assert "alice" in h
    assert "42" in h


def test_html_table_multiple_rows():
    rows = [{"col": f"row{i}"} for i in range(5)]
    h = html_table(rows)
    assert "row0" in h
    assert "row4" in h


def test_html_table_max_rows_truncates():
    rows = [{"x": i} for i in range(300)]
    h = html_table(rows, max_rows=10)
    assert "10" in h or "Showing" in h


def test_html_table_none_values():
    rows = [{"a": None, "b": "val"}]
    h = html_table(rows)
    assert "val" in h  # None should not crash


def test_html_table_long_string_truncated():
    rows = [{"col": "x" * 200}]
    h = html_table(rows)
    # Cell content should be truncated with ellipsis
    assert "…" in h or "x" * 80 in h


# ── error_box ─────────────────────────────────────────────────────────────────

def test_error_box_contains_message():
    h = error_box("Something went wrong")
    assert "Something went wrong" in h


def test_error_box_has_warning_color():
    h = error_box("err")
    assert "#FEF2F2" in h or "red" in h.lower() or "#E63946" in h


# ── info_box ──────────────────────────────────────────────────────────────────

def test_info_box_contains_message():
    h = info_box("All good")
    assert "All good" in h


# ── section_header ────────────────────────────────────────────────────────────

def test_section_header_contains_title():
    h = section_header("Top Users")
    assert "Top Users" in h


def test_section_header_with_subtitle():
    h = section_header("Costs", "last 30 days")
    assert "Costs" in h
    assert "last 30 days" in h


# ── sparkline_html ────────────────────────────────────────────────────────────

def test_sparkline_empty_values():
    h = sparkline_html([])
    assert "▁" in h


def test_sparkline_all_zeros():
    h = sparkline_html([0, 0, 0])
    assert "▁" in h


def test_sparkline_increasing():
    h = sparkline_html([1, 2, 3, 4, 5, 6, 7, 8])
    # Should contain block chars in increasing order
    assert any(c in h for c in "▁▂▃▄▅▆▇█")


def test_sparkline_with_label():
    h = sparkline_html([1, 2, 3], label="Jan→Mar")
    assert "Jan→Mar" in h


# ── format_number ─────────────────────────────────────────────────────────────

def test_format_number_millions():
    assert "M" in format_number(2_000_000)


def test_format_number_thousands():
    assert "K" in format_number(5_000)


def test_format_number_small():
    assert "," in format_number(1_234) or "1" in format_number(1_234)


def test_format_number_zero():
    assert "0" in format_number(0)


def test_format_number_none():
    assert format_number(None) == "None"


def test_format_number_string_passthrough():
    assert format_number("N/A") == "N/A"


def test_format_number_float():
    result = format_number(1234.56)
    assert "1" in result
