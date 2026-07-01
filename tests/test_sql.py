"""
Tests for SQL template generation — every function returns valid SQL strings
with the correct system tables, parameters, and filters. No Spark required.
"""
import pytest
from dashcontrol import sql as Q


# ── Health ───────────────────────────────────────────────────────────────────

def test_health_dbu_today_references_billing():
    s = Q.health_dbu_today()
    assert "system.billing.usage" in s
    assert "CURRENT_DATE" in s


def test_health_active_users_uses_days_param():
    s7  = Q.health_active_users(7)
    s30 = Q.health_active_users(30)
    assert "INTERVAL 7 DAYS" in s7
    assert "INTERVAL 30 DAYS" in s30
    assert "system.access.audit" in s7


def test_health_failed_jobs_uses_hours():
    s = Q.health_failed_jobs(48)
    assert "INTERVAL 48 HOURS" in s
    assert "FAILED" in s
    assert "system.jobs.job_runs" in s


def test_health_table_count_with_filter():
    s = Q.health_table_count("AND table_catalog IN ('main')")
    assert "system.information_schema.tables" in s
    assert "IN ('main')" in s


def test_health_table_count_without_filter():
    s = Q.health_table_count()
    assert "system.information_schema.tables" in s


def test_health_dbu_trend_days():
    s = Q.health_dbu_trend(7)
    assert "INTERVAL 7 DAYS" in s
    assert "GROUP" in s.upper()


# ── Cost ─────────────────────────────────────────────────────────────────────

def test_cost_daily_by_sku_joins_list_prices():
    s = Q.cost_daily_by_sku(30)
    assert "system.billing.usage" in s
    assert "system.billing.list_prices" in s
    assert "sku_name" in s


def test_cost_top_clusters_has_limit():
    s = Q.cost_top_clusters(30, 5)
    assert "LIMIT" in s.upper()
    assert "5" in s


def test_cost_top_jobs_references_metadata():
    s = Q.cost_top_jobs(14)
    assert "job_id" in s
    assert "system.billing.usage" in s


def test_cost_top_users_by_dbu():
    s = Q.cost_top_users_by_dbu(30, 10)
    assert "LIMIT" in s.upper()
    assert "10" in s


def test_cost_burn_rate_has_projection():
    s = Q.cost_burn_rate(30)
    assert "projected_monthly_dbu" in s or "30" in s


# ── Users ────────────────────────────────────────────────────────────────────

def test_users_top_by_queries_audit_table():
    s = Q.users_top_by_queries(30)
    assert "system.access.audit" in s
    assert "user_name" in s
    assert "commandFinish" in s


def test_users_top_by_tables_accessed():
    s = Q.users_top_by_tables_accessed(7)
    assert "system.access.audit" in s
    assert "INTERVAL 7 DAYS" in s


def test_users_inactive_uses_two_windows():
    s = Q.users_inactive(30, 90)
    assert "INTERVAL 30 DAYS" in s
    assert "INTERVAL 90 DAYS" in s
    # Should have a CTE or subquery pattern
    assert "active" in s.lower() or "WITH" in s.upper()


def test_users_permission_changes_actions():
    s = Q.users_permission_changes(7)
    assert "grantPermissions" in s or "updatePermissions" in s


# ── Catalog ──────────────────────────────────────────────────────────────────

def test_catalog_table_inventory_references_schema():
    s = Q.catalog_table_inventory()
    assert "system.information_schema.tables" in s
    assert "BASE TABLE" in s


def test_catalog_table_inventory_with_filter():
    s = Q.catalog_table_inventory("AND table_catalog IN ('main')")
    assert "IN ('main')" in s


def test_catalog_tables_by_schema_groups():
    s = Q.catalog_tables_by_schema()
    upper = s.upper()
    assert "GROUP" in upper
    assert "table_schema" in s


def test_catalog_stale_tables_has_interval():
    s = Q.catalog_stale_tables(90)
    assert "INTERVAL 90 DAYS" in s or "90" in s


def test_catalog_most_accessed_has_limit():
    s = Q.catalog_most_accessed(30, 10)
    assert "LIMIT" in s.upper()


# ── Jobs ─────────────────────────────────────────────────────────────────────

def test_jobs_success_rate_references_runs():
    s = Q.jobs_success_rate(30)
    assert "system.jobs.job_runs" in s
    assert "result_state" in s


def test_jobs_top_failures_joins_jobs():
    s = Q.jobs_top_failures(30)
    assert "system.jobs.jobs" in s
    assert "FAILED" in s


def test_jobs_longest_runs_order_desc():
    s = Q.jobs_longest_runs(7)
    upper = s.upper()
    assert "DESC" in upper
    assert "duration_min" in s or "duration" in s


def test_jobs_daily_run_volume_groups_by_date():
    s = Q.jobs_daily_run_volume(14)
    upper = s.upper()
    assert "GROUP" in upper
    assert "INTERVAL 14 DAYS" in s


# ── Queries ──────────────────────────────────────────────────────────────────

def test_queries_slowest_references_history():
    s = Q.queries_slowest(7)
    assert "system.query.history" in s
    assert "duration" in s


def test_queries_most_expensive_task_duration():
    s = Q.queries_most_expensive(7)
    assert "system.query.history" in s
    assert "total_task_duration" in s or "task" in s


def test_queries_top_users_groups():
    s = Q.queries_top_users(7)
    upper = s.upper()
    assert "GROUP" in upper
    assert "user_name" in s


def test_queries_error_summary_filters_failed():
    s = Q.queries_error_summary(7)
    assert "FAILED" in s
    assert "error_message" in s


# ── Governance ───────────────────────────────────────────────────────────────

def test_governance_tables_without_owners_subquery():
    s = Q.governance_tables_without_owners()
    assert "OWNERSHIP" in s
    assert "system.information_schema.table_privileges" in s


def test_governance_pii_columns_rlike():
    s = Q.governance_pii_columns()
    assert "RLIKE" in s.upper() or "email" in s
    assert "system.information_schema.columns" in s


def test_governance_access_anomalies_actions():
    s = Q.governance_access_anomalies(7)
    assert "accessDenied" in s or "unauthorizedAccess" in s or "Denied" in s


def test_governance_schema_changes_actions():
    s = Q.governance_schema_changes(30)
    assert "createTable" in s or "alterTable" in s
    assert "system.access.audit" in s


def test_all_sql_functions_return_strings():
    """Every SQL function must return a non-empty string."""
    fns = [
        Q.health_dbu_today,
        lambda: Q.health_active_users(30),
        lambda: Q.health_failed_jobs(24),
        lambda: Q.health_table_count(),
        lambda: Q.health_dbu_trend(7),
        lambda: Q.cost_daily_by_sku(30),
        lambda: Q.cost_top_clusters(30),
        lambda: Q.cost_top_jobs(30),
        lambda: Q.cost_top_users_by_dbu(30),
        lambda: Q.cost_burn_rate(30),
        lambda: Q.users_top_by_queries(30),
        lambda: Q.users_top_by_tables_accessed(30),
        lambda: Q.users_inactive(30),
        lambda: Q.users_permission_changes(30),
        lambda: Q.catalog_table_inventory(),
        lambda: Q.catalog_tables_by_schema(),
        lambda: Q.catalog_stale_tables(90),
        lambda: Q.catalog_column_count(),
        lambda: Q.catalog_most_accessed(30),
        lambda: Q.jobs_success_rate(30),
        lambda: Q.jobs_top_failures(30),
        lambda: Q.jobs_longest_runs(30),
        lambda: Q.jobs_daily_run_volume(30),
        lambda: Q.queries_slowest(7),
        lambda: Q.queries_most_expensive(7),
        lambda: Q.queries_top_users(7),
        lambda: Q.queries_error_summary(7),
        lambda: Q.governance_tables_without_owners(),
        lambda: Q.governance_pii_columns(),
        lambda: Q.governance_access_anomalies(7),
        lambda: Q.governance_schema_changes(30),
    ]
    for fn in fns:
        result = fn()
        assert isinstance(result, str) and len(result.strip()) > 10, f"Bad result from {fn}"
