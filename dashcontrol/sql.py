"""
SQL query templates for every Control Center panel.

All functions return plain SQL strings — no Spark dependency.
Parameters are passed as Python arguments so queries are unit-testable.

System tables used:
  system.access.audit          — every audit event
  system.billing.usage         — DBU consumption
  system.billing.list_prices   — SKU list prices
  system.compute.clusters      — cluster inventory
  system.jobs.job_runs         — job run history
  system.jobs.jobs             — job definitions
  system.query.history         — Databricks SQL query history
  system.information_schema.*  — Unity Catalog metadata
"""
from __future__ import annotations


# ── Health ───────────────────────────────────────────────────────────────────

def health_dbu_today() -> str:
    return """
    SELECT COALESCE(ROUND(SUM(usage_quantity), 2), 0) AS dbu_today
    FROM   system.billing.usage
    WHERE  usage_date = CURRENT_DATE
    """


def health_active_users(days: int = 7) -> str:
    return f"""
    SELECT COUNT(DISTINCT user_name) AS active_users
    FROM   system.access.audit
    WHERE  event_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  user_name IS NOT NULL
    """


def health_failed_jobs(hours: int = 24) -> str:
    return f"""
    SELECT COUNT(*) AS failed_jobs
    FROM   system.jobs.job_runs
    WHERE  result_state = 'FAILED'
      AND  run_start_time >= CURRENT_TIMESTAMP - INTERVAL {hours} HOURS
    """


def health_table_count(catalog_filter: str = "") -> str:
    return f"""
    SELECT COUNT(*) AS total_tables
    FROM   system.information_schema.tables
    WHERE  table_type = 'BASE TABLE'
      {catalog_filter}
    """


def health_dbu_trend(days: int = 14) -> str:
    return f"""
    SELECT usage_date,
           ROUND(SUM(usage_quantity), 2) AS dbu
    FROM   system.billing.usage
    WHERE  usage_date >= CURRENT_DATE - INTERVAL {days} DAYS
    GROUP  BY usage_date
    ORDER  BY usage_date
    """


# ── Cost ─────────────────────────────────────────────────────────────────────

def cost_daily_by_sku(days: int = 30) -> str:
    return f"""
    SELECT usage_date,
           sku_name,
           ROUND(SUM(usage_quantity), 3)                         AS dbu,
           ROUND(SUM(usage_quantity * lp.pricing.default), 2)   AS est_usd
    FROM   system.billing.usage u
    LEFT   JOIN system.billing.list_prices lp
             ON lp.sku_name    = u.sku_name
            AND lp.price_start_time <= u.usage_date
            AND (lp.price_end_time IS NULL OR lp.price_end_time > u.usage_date)
    WHERE  usage_date >= CURRENT_DATE - INTERVAL {days} DAYS
    GROUP  BY usage_date, sku_name
    ORDER  BY usage_date DESC, dbu DESC
    """


def cost_top_clusters(days: int = 30, limit: int = 10) -> str:
    return f"""
    SELECT custom_tags['cluster_name']             AS cluster_name,
           usage_metadata['cluster_id']            AS cluster_id,
           ROUND(SUM(usage_quantity), 2)           AS total_dbu,
           COUNT(DISTINCT usage_date)              AS active_days
    FROM   system.billing.usage
    WHERE  usage_date >= CURRENT_DATE - INTERVAL {days} DAYS
      AND  usage_metadata['cluster_id'] IS NOT NULL
    GROUP  BY cluster_name, cluster_id
    ORDER  BY total_dbu DESC
    LIMIT  {limit}
    """


def cost_top_jobs(days: int = 30, limit: int = 10) -> str:
    return f"""
    SELECT usage_metadata['job_id']                AS job_id,
           ROUND(SUM(usage_quantity), 2)           AS total_dbu,
           COUNT(DISTINCT usage_date)              AS active_days
    FROM   system.billing.usage
    WHERE  usage_date >= CURRENT_DATE - INTERVAL {days} DAYS
      AND  usage_metadata['job_id'] IS NOT NULL
    GROUP  BY job_id
    ORDER  BY total_dbu DESC
    LIMIT  {limit}
    """


def cost_top_users_by_dbu(days: int = 30, limit: int = 10) -> str:
    return f"""
    SELECT identity_metadata['run_as']             AS run_as_user,
           ROUND(SUM(usage_quantity), 2)           AS total_dbu
    FROM   system.billing.usage
    WHERE  usage_date >= CURRENT_DATE - INTERVAL {days} DAYS
      AND  identity_metadata['run_as'] IS NOT NULL
    GROUP  BY run_as_user
    ORDER  BY total_dbu DESC
    LIMIT  {limit}
    """


def cost_burn_rate(days: int = 30) -> str:
    return f"""
    SELECT ROUND(SUM(usage_quantity), 2)                       AS total_dbu,
           ROUND(SUM(usage_quantity) / {days}, 2)              AS avg_daily_dbu,
           ROUND(SUM(usage_quantity) / {days} * 30, 2)         AS projected_monthly_dbu,
           COUNT(DISTINCT usage_date)                          AS active_days
    FROM   system.billing.usage
    WHERE  usage_date >= CURRENT_DATE - INTERVAL {days} DAYS
    """


# ── Users ────────────────────────────────────────────────────────────────────

def users_top_by_queries(days: int = 30, limit: int = 20) -> str:
    return f"""
    SELECT user_name,
           COUNT(*)                                             AS total_events,
           COUNT(DISTINCT DATE(event_time))                    AS active_days,
           MIN(event_time)                                     AS first_seen,
           MAX(event_time)                                     AS last_seen
    FROM   system.access.audit
    WHERE  event_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  user_name IS NOT NULL
      AND  action_name IN ('commandFinish','runCommand','commandSubmit',
                           'queries','databricksSqlPermissionsDenied')
    GROUP  BY user_name
    ORDER  BY total_events DESC
    LIMIT  {limit}
    """


def users_top_by_tables_accessed(days: int = 30, limit: int = 20) -> str:
    return f"""
    SELECT user_name,
           COUNT(DISTINCT request_params['full_name_arg'])     AS distinct_tables,
           COUNT(*)                                            AS total_accesses
    FROM   system.access.audit
    WHERE  event_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  user_name IS NOT NULL
      AND  action_name IN ('getTable','getTableData','commandFinish')
      AND  request_params['full_name_arg'] IS NOT NULL
    GROUP  BY user_name
    ORDER  BY distinct_tables DESC
    LIMIT  {limit}
    """


def users_inactive(days: int = 30, lookback: int = 90) -> str:
    return f"""
    WITH active AS (
      SELECT DISTINCT user_name
      FROM   system.access.audit
      WHERE  event_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
    ),
    all_users AS (
      SELECT DISTINCT user_name, MAX(event_time) AS last_seen
      FROM   system.access.audit
      WHERE  event_time >= CURRENT_TIMESTAMP - INTERVAL {lookback} DAYS
      GROUP  BY user_name
    )
    SELECT a.user_name,
           a.last_seen,
           DATEDIFF(CURRENT_TIMESTAMP, a.last_seen) AS days_inactive
    FROM   all_users a
    WHERE  a.user_name NOT IN (SELECT user_name FROM active)
    ORDER  BY days_inactive DESC
    """


def users_permission_changes(days: int = 30, limit: int = 50) -> str:
    return f"""
    SELECT event_time,
           user_name                                           AS changed_by,
           action_name,
           request_params['securable_full_name']              AS target_object,
           request_params['changes']                          AS changes_detail
    FROM   system.access.audit
    WHERE  event_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  action_name IN ('updatePermissions','grantPermissions',
                           'revokePermissions','changeOwner')
    ORDER  BY event_time DESC
    LIMIT  {limit}
    """


# ── Catalog ──────────────────────────────────────────────────────────────────

def catalog_table_inventory(catalog_filter: str = "", limit: int = 500) -> str:
    return f"""
    SELECT table_catalog,
           table_schema,
           table_name,
           table_type,
           created,
           last_altered,
           DATEDIFF(CURRENT_TIMESTAMP, last_altered) AS days_since_altered
    FROM   system.information_schema.tables
    WHERE  table_type = 'BASE TABLE'
      {catalog_filter}
    ORDER  BY last_altered DESC
    LIMIT  {limit}
    """


def catalog_tables_by_schema(catalog_filter: str = "") -> str:
    return f"""
    SELECT table_catalog,
           table_schema,
           COUNT(*) AS table_count
    FROM   system.information_schema.tables
    WHERE  table_type = 'BASE TABLE'
      {catalog_filter}
    GROUP  BY table_catalog, table_schema
    ORDER  BY table_count DESC
    """


def catalog_stale_tables(stale_days: int = 90, catalog_filter: str = "") -> str:
    return f"""
    SELECT table_catalog,
           table_schema,
           table_name,
           last_altered,
           DATEDIFF(CURRENT_TIMESTAMP, last_altered) AS days_stale
    FROM   system.information_schema.tables
    WHERE  table_type = 'BASE TABLE'
      AND  last_altered < CURRENT_TIMESTAMP - INTERVAL {stale_days} DAYS
      {catalog_filter}
    ORDER  BY days_stale DESC
    """


def catalog_column_count(catalog_filter: str = "") -> str:
    return f"""
    SELECT table_catalog,
           table_schema,
           table_name,
           COUNT(*) AS column_count
    FROM   system.information_schema.columns
    WHERE  1=1
      {catalog_filter}
    GROUP  BY table_catalog, table_schema, table_name
    ORDER  BY column_count DESC
    LIMIT  50
    """


def catalog_most_accessed(days: int = 30, limit: int = 20) -> str:
    return f"""
    SELECT request_params['full_name_arg']                     AS table_name,
           COUNT(*)                                            AS access_count,
           COUNT(DISTINCT user_name)                          AS distinct_users
    FROM   system.access.audit
    WHERE  event_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  action_name IN ('getTable','getTableData')
      AND  request_params['full_name_arg'] IS NOT NULL
    GROUP  BY table_name
    ORDER  BY access_count DESC
    LIMIT  {limit}
    """


# ── Jobs ─────────────────────────────────────────────────────────────────────

def jobs_success_rate(days: int = 30) -> str:
    return f"""
    SELECT result_state,
           COUNT(*)                                            AS run_count,
           ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
    FROM   system.jobs.job_runs
    WHERE  run_start_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
    GROUP  BY result_state
    ORDER  BY run_count DESC
    """


def jobs_top_failures(days: int = 30, limit: int = 20) -> str:
    return f"""
    SELECT r.job_id,
           j.name                                             AS job_name,
           COUNT(*)                                           AS failure_count,
           MAX(r.run_start_time)                             AS last_failure
    FROM   system.jobs.job_runs r
    LEFT   JOIN system.jobs.jobs j ON j.job_id = r.job_id
    WHERE  r.run_start_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  r.result_state = 'FAILED'
    GROUP  BY r.job_id, job_name
    ORDER  BY failure_count DESC
    LIMIT  {limit}
    """


def jobs_longest_runs(days: int = 30, limit: int = 20) -> str:
    return f"""
    SELECT r.job_id,
           j.name                                             AS job_name,
           r.run_id,
           r.result_state,
           ROUND((r.run_end_time - r.run_start_time) / 60000, 1)  AS duration_min,
           r.run_start_time
    FROM   system.jobs.job_runs r
    LEFT   JOIN system.jobs.jobs j ON j.job_id = r.job_id
    WHERE  r.run_start_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  r.run_end_time IS NOT NULL
    ORDER  BY duration_min DESC
    LIMIT  {limit}
    """


def jobs_daily_run_volume(days: int = 30) -> str:
    return f"""
    SELECT DATE(run_start_time)                               AS run_date,
           COUNT(*)                                           AS total_runs,
           SUM(CASE WHEN result_state = 'SUCCEEDED' THEN 1 ELSE 0 END) AS succeeded,
           SUM(CASE WHEN result_state = 'FAILED'    THEN 1 ELSE 0 END) AS failed
    FROM   system.jobs.job_runs
    WHERE  run_start_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
    GROUP  BY run_date
    ORDER  BY run_date DESC
    """


# ── Queries (Databricks SQL) ─────────────────────────────────────────────────

def queries_slowest(days: int = 7, limit: int = 20) -> str:
    return f"""
    SELECT user_name,
           ROUND(duration / 1000.0, 1)                       AS duration_sec,
           status,
           LEFT(statement_text, 120)                         AS sql_preview,
           start_time,
           warehouse_id
    FROM   system.query.history
    WHERE  start_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  status = 'FINISHED'
    ORDER  BY duration DESC
    LIMIT  {limit}
    """


def queries_most_expensive(days: int = 7, limit: int = 20) -> str:
    return f"""
    SELECT user_name,
           ROUND(total_task_duration_ms / 1000.0, 1)         AS task_sec,
           ROUND(rows_produced_count / 1e6, 2)               AS rows_m,
           status,
           LEFT(statement_text, 120)                         AS sql_preview,
           start_time
    FROM   system.query.history
    WHERE  start_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
    ORDER  BY total_task_duration_ms DESC
    LIMIT  {limit}
    """


def queries_top_users(days: int = 7, limit: int = 20) -> str:
    return f"""
    SELECT user_name,
           COUNT(*)                                           AS query_count,
           ROUND(AVG(duration) / 1000.0, 1)                 AS avg_duration_sec,
           COUNT(CASE WHEN status = 'FAILED' THEN 1 END)    AS error_count
    FROM   system.query.history
    WHERE  start_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
    GROUP  BY user_name
    ORDER  BY query_count DESC
    LIMIT  {limit}
    """


def queries_error_summary(days: int = 7, limit: int = 30) -> str:
    return f"""
    SELECT LEFT(error_message, 200)                          AS error,
           COUNT(*)                                          AS occurrences,
           COUNT(DISTINCT user_name)                         AS affected_users,
           MAX(start_time)                                   AS last_seen
    FROM   system.query.history
    WHERE  start_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  status = 'FAILED'
      AND  error_message IS NOT NULL
    GROUP  BY error
    ORDER  BY occurrences DESC
    LIMIT  {limit}
    """


# ── Governance ───────────────────────────────────────────────────────────────

def governance_tables_without_owners(catalog_filter: str = "", limit: int = 100) -> str:
    return f"""
    SELECT t.table_catalog,
           t.table_schema,
           t.table_name,
           t.created,
           t.last_altered
    FROM   system.information_schema.tables t
    WHERE  t.table_type = 'BASE TABLE'
      {catalog_filter}
      AND  NOT EXISTS (
             SELECT 1
             FROM   system.information_schema.table_privileges p
             WHERE  p.table_catalog = t.table_catalog
               AND  p.table_schema  = t.table_schema
               AND  p.table_name    = t.table_name
               AND  p.privilege_type = 'OWNERSHIP'
           )
    ORDER  BY t.last_altered ASC
    LIMIT  {limit}
    """


def governance_pii_columns(catalog_filter: str = "", limit: int = 200) -> str:
    return f"""
    SELECT c.table_catalog,
           c.table_schema,
           c.table_name,
           c.column_name,
           c.data_type
    FROM   system.information_schema.columns c
    WHERE  1=1
      {catalog_filter}
      AND  LOWER(c.column_name) RLIKE
             '(email|phone|mobile|ssn|social_security|dob|birth_date|passport|'
             'national_id|tax_id|credit_card|card_number|salary|iban|address|'
             'postcode|zipcode|gender|race|religion)'
    ORDER  BY c.table_catalog, c.table_schema, c.table_name
    LIMIT  {limit}
    """


def governance_access_anomalies(days: int = 7, limit: int = 50) -> str:
    return f"""
    SELECT user_name,
           action_name,
           request_params['full_name_arg']                   AS target_object,
           event_time,
           source_ip_address
    FROM   system.access.audit
    WHERE  event_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  action_name IN ('databricksSqlPermissionsDenied',
                           'unauthorizedAccess',
                           'accessDenied')
    ORDER  BY event_time DESC
    LIMIT  {limit}
    """


def governance_schema_changes(days: int = 30, limit: int = 50) -> str:
    return f"""
    SELECT event_time,
           user_name,
           action_name,
           request_params['full_name_arg']                   AS object_name,
           request_params['changes']                         AS change_detail
    FROM   system.access.audit
    WHERE  event_time >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
      AND  action_name IN ('createTable','deleteTable','alterTable',
                           'createSchema','deleteSchema',
                           'addColumns','dropColumns','renameColumn')
    ORDER  BY event_time DESC
    LIMIT  {limit}
    """
