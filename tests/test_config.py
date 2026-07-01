"""Tests for ControlCenterConfig validation and helpers."""
import pytest
from dashcontrol.config import ControlCenterConfig, CustomPanel, ALL_PANELS


def test_default_config():
    cfg = ControlCenterConfig()
    assert cfg.date_range_days == 30
    assert cfg.row_limit == 500
    assert cfg.panels == list(ALL_PANELS)
    assert cfg.catalogs == []
    assert cfg.custom_panels == []


def test_custom_date_range():
    cfg = ControlCenterConfig(date_range_days=7)
    assert cfg.date_range_days == 7


def test_invalid_date_range_low():
    with pytest.raises(ValueError):
        ControlCenterConfig(date_range_days=0)


def test_invalid_date_range_high():
    with pytest.raises(ValueError):
        ControlCenterConfig(date_range_days=400)


def test_invalid_row_limit():
    with pytest.raises(ValueError):
        ControlCenterConfig(row_limit=0)


def test_invalid_panel_name():
    with pytest.raises(ValueError, match="Unknown panels"):
        ControlCenterConfig(panels=["health", "nonexistent"])


def test_subset_of_panels():
    cfg = ControlCenterConfig(panels=["health", "cost"])
    assert cfg.panels == ["health", "cost"]


def test_catalog_filter_empty():
    cfg = ControlCenterConfig()
    assert cfg.catalog_filter() == ""


def test_catalog_filter_single():
    cfg = ControlCenterConfig(catalogs=["main"])
    f = cfg.catalog_filter()
    assert "main" in f
    assert "IN" in f


def test_catalog_filter_multiple():
    cfg = ControlCenterConfig(catalogs=["main", "hive_metastore"])
    f = cfg.catalog_filter()
    assert "main" in f
    assert "hive_metastore" in f


def test_catalog_filter_custom_col():
    cfg = ControlCenterConfig(catalogs=["main"])
    f = cfg.catalog_filter(col="usage_catalog")
    assert "usage_catalog" in f


def test_custom_panels():
    cp = CustomPanel(title="My Query", sql="SELECT 1")
    cfg = ControlCenterConfig(custom_panels=[cp])
    assert len(cfg.custom_panels) == 1
    assert cfg.custom_panels[0].title == "My Query"


def test_workspace_name():
    cfg = ControlCenterConfig(workspace_name="prod-workspace")
    assert cfg.workspace_name == "prod-workspace"


def test_all_panels_constant():
    assert "health" in ALL_PANELS
    assert "cost" in ALL_PANELS
    assert "users" in ALL_PANELS
    assert "catalog" in ALL_PANELS
    assert "jobs" in ALL_PANELS
    assert "queries" in ALL_PANELS
    assert "governance" in ALL_PANELS
    assert len(ALL_PANELS) == 7
