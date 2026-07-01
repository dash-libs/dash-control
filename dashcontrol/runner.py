"""
Query runner — executes SQL against Databricks system tables.

Spark is imported inside functions only (never at module level) so this
module can be imported and tested without a live Spark session.
"""
from __future__ import annotations
from typing import Optional


class QueryResult:
    """Holds the result of a panel query with metadata."""

    def __init__(self, rows: list[dict], sql: str, error: Optional[str] = None):
        self.rows = rows
        self.sql = sql
        self.error = error
        self.ok = error is None

    def __len__(self) -> int:
        return len(self.rows)

    def column_names(self) -> list[str]:
        return list(self.rows[0].keys()) if self.rows else []

    def column_values(self, col: str) -> list:
        return [r.get(col) for r in self.rows]

    def first_value(self, col: str, default=None):
        return self.rows[0].get(col, default) if self.rows else default

    def to_csv(self) -> str:
        if not self.rows:
            return ""
        cols = self.column_names()
        lines = [",".join(str(c) for c in cols)]
        for row in self.rows:
            lines.append(",".join(str(row.get(c, "")) for c in cols))
        return "\n".join(lines)


def run_query(sql: str, limit: int = 500) -> QueryResult:
    """
    Execute a SQL query against Databricks system tables.

    Uses the active SparkSession — must be run inside a Databricks notebook
    (or any environment where a SparkSession is already active).

    Parameters
    ----------
    sql   : SQL string (use functions from dashcontrol.sql)
    limit : max rows to return

    Returns
    -------
    QueryResult with .rows (list of dicts) and .ok / .error
    """
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.getActiveSession()
        if spark is None:
            return QueryResult([], sql, error="No active Spark session. Run inside a Databricks notebook.")
        df = spark.sql(sql.strip())
        rows = [r.asDict() for r in df.limit(limit).collect()]
        return QueryResult(rows, sql)
    except Exception as e:
        return QueryResult([], sql, error=str(e))


def run_query_safe(sql: str, limit: int = 500) -> QueryResult:
    """
    Same as run_query but returns a QueryResult with error set (never raises)
    even for system tables that don't exist on the current workspace tier.
    """
    try:
        return run_query(sql, limit)
    except Exception as e:
        return QueryResult([], sql, error=str(e))
