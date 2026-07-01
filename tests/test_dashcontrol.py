"""Smoke tests — no Spark required."""


def test_import():
    import dashcontrol
    assert hasattr(dashcontrol, "__version__")


def test_launch_importable():
    from dashcontrol import launch
    assert callable(launch)


def test_public_api():
    from dashcontrol import ControlCenterConfig, CustomPanel
    cfg = ControlCenterConfig()
    assert cfg.date_range_days == 30
    assert "health" in cfg.panels


def test_custom_panel_importable():
    from dashcontrol import CustomPanel
    cp = CustomPanel(title="Test", sql="SELECT 1")
    assert cp.title == "Test"
