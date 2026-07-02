"""
Databricks Control Center — main launch() UI.

One call gives you a fully-tabbed dashboard across:
  Health · Cost · Users · Catalog · Jobs · Queries · Governance · Custom
"""
from __future__ import annotations
from dashcontrol.config import ControlCenterConfig


def launch(config: ControlCenterConfig = None):
    try:
        import ipywidgets as w
        from IPython.display import display
    except ImportError:
        raise RuntimeError("ipywidgets required. Run: %pip install ipywidgets")

    import dashui
    from dashcontrol.runner import run_query_safe
    from dashcontrol import sql as Q
    from dashcontrol.formatters import (
        html_table, stat_tile, stat_row, error_box, info_box,
        section_header, sparkline_html, format_number, _TEAL, _RED, _AMBER, _GREEN,
    )

    cfg = config or ControlCenterConfig()

    # ── Global controls ───────────────────────────────────────────────────────
    days_slider = w.IntSlider(
        value=cfg.date_range_days, min=1, max=90, step=1,
        description="Days:", style={"description_width": "40px"},
        layout=w.Layout(width="320px"),
    )
    catalog_text = w.Text(
        value=", ".join(cfg.catalogs),
        description="Catalogs:",
        placeholder="main, hive_metastore (blank = all)",
        style={"description_width": "70px"},
        layout=w.Layout(width="360px"),
    )
    workspace_label = w.HTML(
        value=f"<div style='font-size:11px;color:#6b7280;padding:4px 0'>"
              f"Workspace: <b>{cfg.workspace_name or 'auto-detected'}</b></div>"
    )

    def _days() -> int:
        return days_slider.value

    def _cat_filter() -> str:
        cats = [c.strip() for c in catalog_text.value.split(",") if c.strip()]
        if not cats:
            return ""
        quoted = ", ".join(f"'{c}'" for c in cats)
        return f"AND table_catalog IN ({quoted})"

    # ── Panel builder helper ──────────────────────────────────────────────────
    def _panel(sections_fn) -> tuple:
        """Create a (load_btn, output) pair and wire the click."""
        out = dashui.output_panel()
        btn = dashui.action_button("Load", style="info", emoji="▶")

        def _on_click(b):
            btn.disabled = True
            btn.description = "Loading…"
            with out:
                out.clear_output()
                try:
                    sections_fn(out)
                except Exception as e:
                    import ipywidgets as _w
                    from IPython.display import display as _d
                    _d(_w.HTML(error_box(str(e))))
            btn.disabled = False
            btn.description = "Refresh"

        btn.on_click(_on_click)
        return btn, out

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: HEALTH
    # ─────────────────────────────────────────────────────────────────────────
    def _health(out):
        from IPython.display import display as _d
        import ipywidgets as _w

        d = _days()
        dbu   = run_query_safe(Q.health_dbu_today(), 1)
        users = run_query_safe(Q.health_active_users(d), 1)
        jobs  = run_query_safe(Q.health_failed_jobs(24), 1)
        tbls  = run_query_safe(Q.health_table_count(_cat_filter()), 1)
        trend = run_query_safe(Q.health_dbu_trend(min(d, 14)))

        dbu_val   = format_number(dbu.first_value("dbu_today", 0))
        user_val  = format_number(users.first_value("active_users", 0))
        job_val   = jobs.first_value("failed_jobs", 0)
        tbl_val   = format_number(tbls.first_value("total_tables", 0))
        job_color = _RED if (job_val or 0) > 0 else _GREEN

        tiles = stat_row([
            stat_tile("DBU Today",              dbu_val,  _TEAL),
            stat_tile(f"Active Users ({d}d)",   user_val, _TEAL),
            stat_tile("Failed Jobs (24h)",       job_val,  job_color),
            stat_tile("Total Tables",            tbl_val,  _TEAL),
        ])

        sparkline = ""
        if trend.ok and trend.rows:
            vals = [float(r.get("dbu", 0) or 0) for r in trend.rows]
            dates = [str(r.get("usage_date", ""))[-5:] for r in trend.rows]
            label = f"{dates[0]} → {dates[-1]}" if dates else ""
            sparkline = (
                section_header("DBU Trend") +
                f"<div style='padding:8px 0'>{sparkline_html(vals, label)}</div>"
            )

        _d(_w.HTML(tiles + sparkline))

    health_btn, health_out = _panel(_health)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: COST
    # ─────────────────────────────────────────────────────────────────────────
    def _cost(out):
        from IPython.display import display as _d
        import ipywidgets as _w

        d = _days()
        burn  = run_query_safe(Q.cost_burn_rate(d), 1)
        skus  = run_query_safe(Q.cost_daily_by_sku(d), cfg.row_limit)
        clust = run_query_safe(Q.cost_top_clusters(d), 10)
        jobs  = run_query_safe(Q.cost_top_jobs(d), 10)
        users = run_query_safe(Q.cost_top_users_by_dbu(d), 10)

        total  = format_number(burn.first_value("total_dbu", 0))
        daily  = format_number(burn.first_value("avg_daily_dbu", 0))
        proj   = format_number(burn.first_value("projected_monthly_dbu", 0))

        tiles = stat_row([
            stat_tile(f"Total DBU ({d}d)",        total, _TEAL),
            stat_tile("Avg Daily DBU",             daily, _TEAL),
            stat_tile("Projected Monthly DBU",     proj,  _AMBER),
        ])

        html = tiles
        if skus.ok:
            html += section_header("Daily DBU by SKU")
            html += html_table(skus.rows[:30], highlight_col="dbu")
        if clust.ok:
            html += section_header("Top Clusters by DBU")
            html += html_table(clust.rows)
        if jobs.ok:
            html += section_header("Top Jobs by DBU")
            html += html_table(jobs.rows)
        if users.ok:
            html += section_header("Top Users by DBU")
            html += html_table(users.rows)

        for res in [skus, clust, jobs, users]:
            if not res.ok:
                html += error_box(res.error)

        _d(_w.HTML(html))

    cost_btn, cost_out = _panel(_cost)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: USERS
    # ─────────────────────────────────────────────────────────────────────────
    def _users(out):
        from IPython.display import display as _d
        import ipywidgets as _w

        d = _days()
        top_q  = run_query_safe(Q.users_top_by_queries(d), 20)
        top_t  = run_query_safe(Q.users_top_by_tables_accessed(d), 20)
        inact  = run_query_safe(Q.users_inactive(d, min(d * 3, 90)), 20)
        perms  = run_query_safe(Q.users_permission_changes(d), 30)

        html = ""
        if top_q.ok:
            html += section_header("Top Users by Activity", f"last {d} days")
            html += html_table(top_q.rows)
        if top_t.ok:
            html += section_header("Top Users by Tables Accessed")
            html += html_table(top_t.rows)
        if inact.ok and inact.rows:
            html += section_header("Inactive Users", f"not seen in {d}d")
            html += html_table(inact.rows, highlight_col="days_inactive")
        if perms.ok and perms.rows:
            html += section_header("Recent Permission Changes")
            html += html_table(perms.rows, highlight_col="action_name")

        for res in [top_q, top_t, inact, perms]:
            if not res.ok:
                html += error_box(res.error)

        _d(_w.HTML(html))

    users_btn, users_out = _panel(_users)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: CATALOG
    # ─────────────────────────────────────────────────────────────────────────
    def _catalog(out):
        from IPython.display import display as _d
        import ipywidgets as _w

        cf = _cat_filter()
        d  = _days()
        inv    = run_query_safe(Q.catalog_tables_by_schema(cf), 100)
        stale  = run_query_safe(Q.catalog_stale_tables(90, cf), 50)
        hot    = run_query_safe(Q.catalog_most_accessed(d, 20))
        cols   = run_query_safe(Q.catalog_column_count(cf), 30)

        html = ""
        if inv.ok:
            total = sum(r.get("table_count", 0) or 0 for r in inv.rows)
            html += stat_row([stat_tile("Total Tables", format_number(total), _TEAL)])
            html += section_header("Tables by Schema")
            html += html_table(inv.rows)
        if stale.ok and stale.rows:
            html += section_header("Stale Tables (90+ days unmodified)")
            html += html_table(stale.rows, highlight_col="days_stale")
        if hot.ok:
            html += section_header(f"Most Accessed Tables (last {d}d)")
            html += html_table(hot.rows)
        if cols.ok:
            html += section_header("Widest Tables (by column count)")
            html += html_table(cols.rows)

        for res in [inv, stale, hot, cols]:
            if not res.ok:
                html += error_box(res.error)

        _d(_w.HTML(html))

    catalog_btn, catalog_out = _panel(_catalog)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: JOBS
    # ─────────────────────────────────────────────────────────────────────────
    def _jobs(out):
        from IPython.display import display as _d
        import ipywidgets as _w

        d = _days()
        rates  = run_query_safe(Q.jobs_success_rate(d))
        fails  = run_query_safe(Q.jobs_top_failures(d), 20)
        slow   = run_query_safe(Q.jobs_longest_runs(d), 20)
        volume = run_query_safe(Q.jobs_daily_run_volume(d))

        html = ""
        if rates.ok and rates.rows:
            total = sum(r.get("run_count", 0) or 0 for r in rates.rows)
            success = next((r["run_count"] for r in rates.rows if r.get("result_state") == "SUCCEEDED"), 0)
            rate_pct = round(success / total * 100, 1) if total else 0
            color = _GREEN if rate_pct >= 95 else (_AMBER if rate_pct >= 80 else _RED)
            html += stat_row([
                stat_tile(f"Success Rate ({d}d)", f"{rate_pct}%", color),
                stat_tile("Total Runs", format_number(total), _TEAL),
            ])
            html += section_header("Run State Breakdown")
            html += html_table(rates.rows, highlight_col="result_state")
        if fails.ok and fails.rows:
            html += section_header("Top Failing Jobs")
            html += html_table(fails.rows, highlight_col="failure_count")
        if slow.ok:
            html += section_header("Longest Running Jobs")
            html += html_table(slow.rows, highlight_col="duration_min")
        if volume.ok and volume.rows:
            html += section_header("Daily Run Volume")
            html += html_table(volume.rows)

        for res in [rates, fails, slow, volume]:
            if not res.ok:
                html += error_box(res.error)

        _d(_w.HTML(html))

    jobs_btn, jobs_out = _panel(_jobs)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: QUERIES
    # ─────────────────────────────────────────────────────────────────────────
    def _queries(out):
        from IPython.display import display as _d
        import ipywidgets as _w

        d = min(_days(), 7)  # query.history can be large; cap at 7d default
        slow  = run_query_safe(Q.queries_slowest(d), 20)
        exp   = run_query_safe(Q.queries_most_expensive(d), 20)
        top   = run_query_safe(Q.queries_top_users(d), 20)
        errs  = run_query_safe(Q.queries_error_summary(d), 20)

        html = ""
        if slow.ok:
            html += section_header(f"Slowest Queries (last {d}d)")
            html += html_table(slow.rows, highlight_col="duration_sec")
        if exp.ok:
            html += section_header("Most Expensive Queries (by task time)")
            html += html_table(exp.rows, highlight_col="task_sec")
        if top.ok:
            html += section_header("Top Query Authors")
            html += html_table(top.rows)
        if errs.ok and errs.rows:
            html += section_header("Most Common Query Errors")
            html += html_table(errs.rows, highlight_col="occurrences")

        for res in [slow, exp, top, errs]:
            if not res.ok:
                html += error_box(res.error)

        _d(_w.HTML(html))

    queries_btn, queries_out = _panel(_queries)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: GOVERNANCE
    # ─────────────────────────────────────────────────────────────────────────
    def _governance(out):
        from IPython.display import display as _d
        import ipywidgets as _w

        cf = _cat_filter()
        d  = _days()
        noown  = run_query_safe(Q.governance_tables_without_owners(cf), 50)
        pii    = run_query_safe(Q.governance_pii_columns(cf), 100)
        anomal = run_query_safe(Q.governance_access_anomalies(d), 30)
        schema = run_query_safe(Q.governance_schema_changes(d), 30)

        html = ""
        noown_n = len(noown.rows) if noown.ok else "?"
        pii_n   = len(pii.rows)   if pii.ok   else "?"
        anomal_n= len(anomal.rows)if anomal.ok else "?"

        noown_color  = _RED if noown_n and noown_n != "?" and noown_n > 0  else _GREEN
        anomal_color = _RED if anomal_n and anomal_n != "?" and anomal_n > 0 else _GREEN

        html += stat_row([
            stat_tile("Tables Without Owners", noown_n,  noown_color),
            stat_tile("PII Columns Detected",  pii_n,    _AMBER),
            stat_tile(f"Access Denials ({d}d)", anomal_n, anomal_color),
        ])

        if noown.ok and noown.rows:
            html += section_header("Tables Without Owners")
            html += html_table(noown.rows)
        elif noown.ok:
            html += section_header("Tables Without Owners")
            html += info_box("All tables have owners. Good.")

        if pii.ok and pii.rows:
            html += section_header("Potential PII Columns (pattern-matched)")
            html += html_table(pii.rows)

        if anomal.ok and anomal.rows:
            html += section_header(f"Access Denials / Anomalies (last {d}d)")
            html += html_table(anomal.rows, highlight_col="action_name")

        if schema.ok and schema.rows:
            html += section_header(f"Schema Changes (last {d}d)")
            html += html_table(schema.rows, highlight_col="action_name")

        for res in [noown, pii, anomal, schema]:
            if not res.ok:
                html += error_box(res.error)

        _d(_w.HTML(html))

    gov_btn, gov_out = _panel(_governance)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: CUSTOM
    # ─────────────────────────────────────────────────────────────────────────
    custom_title = w.Text(description="Title:", placeholder="My panel title")
    custom_sql   = w.Textarea(
        description="SQL:",
        placeholder="SELECT * FROM system.access.audit LIMIT 20",
        layout=w.Layout(width="100%", height="100px"),
    )
    custom_btn = dashui.action_button("Run Custom Query", style="warning", emoji="⚡")
    custom_out = dashui.output_panel()

    # Pre-wire any custom panels from config
    _config_custom_widgets = []
    for cp in cfg.custom_panels:
        cp_out = dashui.output_panel()
        cp_btn = dashui.action_button(f"Load: {cp.title}", style="info", emoji="▶")
        _sql_closure = cp.sql

        def _make_handler(s, o):
            def _h(b):
                from IPython.display import display as _d
                import ipywidgets as _w
                r = run_query_safe(s, cfg.row_limit)
                with o:
                    o.clear_output()
                    _d(_w.HTML(
                        html_table(r.rows) if r.ok else error_box(r.error)
                    ))
            return _h

        cp_btn.on_click(_make_handler(_sql_closure, cp_out))
        _config_custom_widgets.extend([cp_btn, cp_out])

    def on_custom(b):
        sql = custom_sql.value.strip()
        if not sql:
            return
        with custom_out:
            custom_out.clear_output()
            from IPython.display import display as _d
            import ipywidgets as _w
            r = run_query_safe(sql, cfg.row_limit)
            _d(_w.HTML(
                html_table(r.rows) if r.ok else error_box(r.error)
            ))

    custom_btn.on_click(on_custom)

    # ── Assemble tabs ─────────────────────────────────────────────────────────
    panel_map = {
        "health":     ("🏥 Health",     w.VBox([health_btn, health_out])),
        "cost":       ("💰 Cost",       w.VBox([cost_btn, cost_out])),
        "users":      ("👥 Users",      w.VBox([users_btn, users_out])),
        "catalog":    ("📦 Catalog",    w.VBox([catalog_btn, catalog_out])),
        "jobs":       ("⚙️ Jobs",       w.VBox([jobs_btn, jobs_out])),
        "queries":    ("🔍 Queries",    w.VBox([queries_btn, queries_out])),
        "governance": ("🛡️ Governance", w.VBox([gov_btn, gov_out])),
    }

    tab = w.Tab()
    children, titles = [], []
    for panel_id in cfg.panels:
        if panel_id in panel_map:
            title, content = panel_map[panel_id]
            children.append(content)
            titles.append(title)

    # Custom tab always last
    custom_content = w.VBox(
        _config_custom_widgets + [custom_title, custom_sql, custom_btn, custom_out]
    )
    children.append(custom_content)
    titles.append("➕ Custom")

    tab.children = children
    for i, t in enumerate(titles):
        tab.set_title(i, t)

    ui = dashui.card([
        dashui.header(
            f"Databricks Control Center{' — ' + cfg.workspace_name if cfg.workspace_name else ''}",
            library="dashcontrol",
            emoji="🎛️",
        ),
        dashui.html(
            "<div style='font-size:11px;color:#6b7280;margin-bottom:4px'>"
            "Click a tab then <b>Load</b> to query system tables. "
            "Results are lazy-loaded and cached until you Refresh.</div>"
        ),
        w.HBox([days_slider, catalog_text]),
        workspace_label,
        tab,
    ])
    display(ui)
