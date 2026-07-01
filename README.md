# dash-control

**Databricks Control Center** — a live, 8-panel system-table dashboard for platform, governance, cost, and operations teams. One `%pip install` + one `launch()` call gives you an always-on view of your entire Databricks workspace.

```python
%pip install dash-control
from dashcontrol import launch, ControlCenterConfig

config = ControlCenterConfig(
    date_range_days=30,
    catalogs=["main", "analytics"],
)
launch(config)
```

## Panels

| Panel | What it shows |
|---|---|
| **Health** | DBU today, active users, failed jobs (last 24 h), total table count, 7-day DBU sparkline |
| **Cost** | Daily spend by SKU, top clusters, top jobs, top users by DBU, burn-rate projection |
| **Users** | Top users by query count & tables accessed, inactive users, permission changes |
| **Catalog** | Table inventory, tables by schema, stale tables, column count distribution, most-accessed tables |
| **Jobs** | Success rate, top failures, longest runs, daily run volume trend |
| **Queries** | Slowest queries, most expensive queries, top users, error summary |
| **Governance** | Tables without owners, PII columns, access anomalies, schema changes |
| **Custom** | Run any SQL against system tables; define custom panels in `ControlCenterConfig` |

## Configuration

```python
from dashcontrol import ControlCenterConfig, CustomPanel

config = ControlCenterConfig(
    date_range_days=14,          # default look-back window (also adjustable in the UI)
    catalogs=["main"],           # limit catalog scope; empty = all catalogs
    panels=["health", "cost"],   # show only these panels
    row_limit=200,               # max rows per table result
    workspace_name="prod",       # displayed in the header
    custom_panels=[
        CustomPanel(
            name="My Query",
            sql="SELECT user_name, COUNT(*) AS cnt FROM system.access.audit GROUP BY 1",
            description="Custom audit rollup",
        )
    ],
)
```

## Requirements

- Databricks Runtime 13.3 LTS or later (system tables must be enabled)
- Unity Catalog workspace
- `ipywidgets` (included as a dependency)

## Architecture

Every panel is **lazy-loaded** — clicking Load runs the query; nothing executes on `launch()`. Queries target Databricks system tables (`system.billing.*`, `system.access.audit`, `system.jobs.*`, `system.query.history`, `system.information_schema.*`). All queries degrade gracefully: if a system table isn't available on your workspace tier, the panel shows an info banner instead of crashing.

## Part of the DashLibs suite

| Package | Purpose |
|---|---|
| [dash-dq](https://pypi.org/project/dash-dq/) | 60+ data quality checks |
| [dash-synthetic](https://pypi.org/project/dash-synthetic/) | Synthetic data generation |
| [dash-observe](https://pypi.org/project/dash-observe/) | Freshness, volume & schema monitoring |
| [dash-gov](https://pypi.org/project/dash-gov/) | Table/column lineage + role classification |
| [dash-ontology](https://pypi.org/project/dash-ontology/) | Auto-inferred business ontology from lineage |
| **dash-control** | Control Center — this package |

## License

Apache 2.0
