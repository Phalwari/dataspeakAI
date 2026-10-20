"""Offline HTML export checks for distinct unavailable and zero KPI values."""

import re
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

    csp_meta = re.search(
        r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"', content
    )
    assert csp_meta is not None
    assert "default-src 'none'" in [
        directive.strip() for directive in csp_meta.group(1).split(";")
    ]


def test_export_labels_fallback_and_escapes_summary(monkeypatch):
    connection = SimpleNamespace(name="Sample database", database=None, db_type="sqlite", status="active")
    monkeypatch.setattr(insights, "_owned_connection", lambda *_args: connection)
    monkeypatch.setattr(
        insights.db_pipeline_service, "run_db_pipeline",
        lambda **_kwargs: {
            "key_metrics": [],
            "executive_summary": {
                "source": "deterministic_fallback",
                "executive_summary": "Computed 2 records <script>alert(1)</script>",
            },
        },
    )
    response = insights.export_insights(
        connection_id=1, current_user=SimpleNamespace(tenant_id=1, id=1), db=object(),
    )
    content = response.body.decode("utf-8")
    assert "Auto-generated summary (AI unavailable)" in content
    assert "Computed 2 records &lt;script&gt;alert(1)&lt;/script&gt;" in content
    assert "<script>alert(1)</script>" not in content


def test_export_labels_llm_summary(monkeypatch):
    connection = SimpleNamespace(name="Sample database", database=None, db_type="sqlite", status="active")
    monkeypatch.setattr(insights, "_owned_connection", lambda *_args: connection)
    monkeypatch.setattr(
        insights.db_pipeline_service, "run_db_pipeline",
        lambda **_kwargs: {
            "key_metrics": [],
            "executive_summary": {"source": "llm", "executive_summary": "Verified fixture summary"},
        },
    )
    response = insights.export_insights(
        connection_id=1, current_user=SimpleNamespace(tenant_id=1, id=1), db=object(),
    )
    content = response.body.decode("utf-8")
    assert "AI Executive Summary" in content
    assert "Verified fixture summary" in content
    assert "AI unavailable" not in content
