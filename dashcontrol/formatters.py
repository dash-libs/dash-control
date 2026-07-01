"""
Pure-Python formatting utilities — no Spark dependency.

Converts query result rows (list[dict]) into styled HTML tables,
stat tiles, trend sparklines, and CSV exports for the Control Center UI.
"""
from __future__ import annotations
from typing import Optional

# Colour palette
_TEAL   = "#2A9D90"
_AMBER  = "#F4A261"
_RED    = "#E63946"
_GREEN  = "#2DC653"
_GREY   = "#6B7280"
_LIGHT  = "#F9FAFB"
_BORDER = "#E5E7EB"


def stat_tile(label: str, value, color: str = _TEAL, unit: str = "") -> str:
    """Render a single KPI tile (label + big number)."""
    return (
        f"<div style='display:inline-block;padding:14px 20px;margin:6px;"
        f"border-radius:8px;background:{_LIGHT};border:1px solid {_BORDER};"
        f"min-width:140px;text-align:center'>"
        f"<div style='font-size:26px;font-weight:700;color:{color}'>"
        f"{value}{unit}</div>"
        f"<div style='font-size:11px;color:{_GREY};margin-top:4px'>{label}</div>"
        f"</div>"
    )


def stat_row(tiles: list[str]) -> str:
    """Wrap stat tiles in a flex row."""
    inner = "".join(tiles)
    return f"<div style='display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px'>{inner}</div>"


def html_table(
    rows: list[dict],
    highlight_col: Optional[str] = None,
    max_rows: int = 200,
    col_widths: Optional[dict] = None,
) -> str:
    """
    Convert a list of row-dicts to a styled HTML table.

    highlight_col — column whose values determine row background colour
                    (high numeric value = amber, error strings = red)
    """
    if not rows:
        return "<div style='color:#9ca3af;font-size:12px;padding:8px'>No data</div>"

    cols = list(rows[0].keys())
    col_widths = col_widths or {}

    def _header(col: str) -> str:
        w = f"min-width:{col_widths[col]};" if col in col_widths else ""
        label = col.replace("_", " ").title()
        return (
            f"<th style='padding:6px 10px;background:#F3F4F6;text-align:left;"
            f"font-size:11px;color:{_GREY};font-weight:600;white-space:nowrap;{w}'>"
            f"{label}</th>"
        )

    def _cell(val, col: str) -> str:
        text = "" if val is None else str(val)
        # Truncate long strings
        display = text[:80] + "…" if len(text) > 80 else text
        return (
            f"<td style='padding:5px 10px;font-size:12px;"
            f"font-family:monospace;border-top:1px solid {_BORDER}'>"
            f"{display}</td>"
        )

    def _row_bg(row: dict) -> str:
        if highlight_col and highlight_col in row:
            v = row[highlight_col]
            if isinstance(v, str) and any(k in v.upper() for k in ("FAIL", "ERROR", "DENIED")):
                return f"background:#FEF2F2;"
        return ""

    headers = "".join(_header(c) for c in cols)
    body_rows = ""
    for r in rows[:max_rows]:
        bg = _row_bg(r)
        cells = "".join(_cell(r.get(c), c) for c in cols)
        body_rows += f"<tr style='{bg}'>{cells}</tr>"

    footer = ""
    if len(rows) > max_rows:
        footer = (
            f"<tr><td colspan='{len(cols)}' style='padding:6px 10px;"
            f"font-size:11px;color:{_GREY};text-align:center'>"
            f"Showing {max_rows} of {len(rows)} rows</td></tr>"
        )

    return (
        f"<div style='overflow-x:auto'>"
        f"<table style='border-collapse:collapse;width:100%;font-size:12px'>"
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{body_rows}{footer}</tbody>"
        f"</table></div>"
    )


def error_box(message: str) -> str:
    """Red alert box for query errors."""
    return (
        f"<div style='padding:10px 14px;background:#FEF2F2;border:1px solid #FCA5A5;"
        f"border-radius:6px;color:{_RED};font-size:12px;font-family:monospace'>"
        f"⚠ {message}</div>"
    )


def info_box(message: str) -> str:
    """Blue info box."""
    return (
        f"<div style='padding:10px 14px;background:#EFF6FF;border:1px solid #BFDBFE;"
        f"border-radius:6px;color:#1D4ED8;font-size:12px'>"
        f"ℹ {message}</div>"
    )


def section_header(title: str, subtitle: str = "") -> str:
    sub = f"<span style='font-size:11px;color:{_GREY};margin-left:8px'>{subtitle}</span>" if subtitle else ""
    return (
        f"<div style='font-weight:600;font-size:13px;color:#374151;"
        f"margin:12px 0 6px;padding-bottom:4px;border-bottom:1px solid {_BORDER}'>"
        f"{title}{sub}</div>"
    )


def sparkline_html(values: list[float], label: str = "") -> str:
    """
    Minimal ASCII sparkline for trend data (no JS/SVG required).
    Uses Unicode block characters: ▁▂▃▄▅▆▇█
    """
    blocks = "▁▂▃▄▅▆▇█"
    if not values or all(v == 0 for v in values):
        return f"<span style='font-family:monospace;color:{_GREY}'>{'▁' * 10}</span>"
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    chars = "".join(blocks[min(7, int((v - mn) / rng * 7))] for v in values)
    return (
        f"<span style='font-family:monospace;font-size:14px;color:{_TEAL}'>{chars}</span>"
        + (f"<span style='font-size:10px;color:{_GREY};margin-left:4px'>{label}</span>" if label else "")
    )


def format_number(n) -> str:
    """Format large numbers with K/M suffixes."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,.0f}" if n == int(n) else f"{n:,.2f}"
