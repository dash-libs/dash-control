"""
ControlCenterConfig — user-facing configuration for the Control Center.

All fields have sensible defaults so teams can call launch() with zero config,
or pre-wire a domain-specific dashboard by passing a config object.
"""
from __future__ import annotations
from dataclasses import dataclass, field

ALL_PANELS = ["health", "cost", "users", "catalog", "jobs", "queries", "governance"]


@dataclass
class CustomPanel:
    title: str
    sql: str
    description: str = ""


@dataclass
class ControlCenterConfig:
    """
    Configuration for the Databricks Control Center.

    Parameters
    ----------
    date_range_days
        Default lookback window for all time-based queries (default: 30).
    catalogs
        List of catalogs to scope table/lineage queries to.
        Empty list means all visible catalogs.
    panels
        Which built-in panels to show. Defaults to all.
    custom_panels
        User-defined SQL panels appended after the built-in tabs.
    row_limit
        Max rows returned per panel query (default: 500).
    workspace_name
        Optional display name shown in the dashboard header.
    """
    date_range_days: int = 30
    catalogs: list[str] = field(default_factory=list)
    panels: list[str] = field(default_factory=lambda: list(ALL_PANELS))
    custom_panels: list[CustomPanel] = field(default_factory=list)
    row_limit: int = 500
    workspace_name: str = ""

    def __post_init__(self):
        unknown = set(self.panels) - set(ALL_PANELS)
        if unknown:
            raise ValueError(f"Unknown panels: {unknown}. Valid: {ALL_PANELS}")
        if self.date_range_days < 1 or self.date_range_days > 365:
            raise ValueError("date_range_days must be between 1 and 365")
        if self.row_limit < 1 or self.row_limit > 10_000:
            raise ValueError("row_limit must be between 1 and 10,000")

    def catalog_filter(self, col: str = "table_catalog") -> str:
        """SQL WHERE fragment to filter by configured catalogs."""
        if not self.catalogs:
            return ""
        quoted = ", ".join(f"'{c}'" for c in self.catalogs)
        return f"AND {col} IN ({quoted})"
