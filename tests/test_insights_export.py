"""Offline HTML export checks for distinct unavailable and zero KPI values."""

from types import SimpleNamespace

from routers import insights


def test_export_shows_unavailable_as_na_and_preserves_zero(monkeypatch):
    connection = SimpleNamespace(name="Sample database", database=None, db_type="sqlite", status="active")
    monkeypatch.setattr(insights, "_owned_connection", lambda *_args: connection)
    monkeypatch.setattr(
        insights.db_pipeline_service,
        "run_db_pipeline",
        lambda **_kwargs: {
            "key_metrics": [
                {"label": "Unavailable <script>metric</script>", "value": None, "status": "unavailable"},
                {"label": "Failed metric", "value": "$9", "status": "error"},
                {"label": "Zero revenue", "value": "$0", "status": "zero"},
                {"label": "Zero count", "value": 0, "status": "zero"},
            ],
        },
    )

    response = insights.export_insights(
        connection_id=1,
        current_user=SimpleNamespace(tenant_id=1, id=1),
        db=object(),
    )
    content = response.body.decode("utf-8")

    assert content.count('<div class="metric-value">N/A</div>') == 2
    assert '<div class="metric-value">$0</div>' in content
    assert '<div class="metric-value">0</div>' in content
    assert '&lt;script&gt;metric&lt;/script&gt;' in content
    assert '<script>metric</script>' not in content
