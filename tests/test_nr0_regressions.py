"""
tests/test_nr0_regressions.py
-----------------------------
Permanent regression test suite for the six audit defect families (Task NR-0.1-A-T03).
Covers issues I-01, I-02, I-08, I-09, I-11, and I-14.

Engineering Rule:
- Each defect test asserts the DESIRED SAFE BEHAVIOR.
- Unfixed audit defects are marked with @pytest.mark.xfail(strict=True, reason=...)
  referencing the owning fix sprint.
- When an owning fix sprint repairs the defect in the future, strict=True causes
  pytest to report an XPASS error, guaranteeing that the marker is removed and the
  test becomes a permanent passing regression test.
- Legitimate control cases are included alongside defect cases to prove test validity.
"""

import re
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

import models
import schemas
from services.sql_engine import execute_safe_sql
from services.citation_service import CitationService
from routers.analytics import get_admin_tenants


# ===========================================================================
# 1. Family I-01: Tenant Admin Privilege Escalation (Owned by NR-1.1-A)
# ===========================================================================

def test_probe_i01_control_tenant_admin_own_tenant_access(nr0_scenario, isolated_db: Session):
    """Control: A tenant admin should be able to query their own tenant successfully."""
    admin_u1 = nr0_scenario["users"]["u1_admin"]
    t1 = nr0_scenario["tenants"]["t1"]
    
    tenant_record = isolated_db.query(models.Tenant).filter(models.Tenant.id == admin_u1.tenant_id).first()
    assert tenant_record is not None
    assert tenant_record.name == "Acme Corp"


@pytest.mark.xfail(
    strict=True,
    reason="Issue I-01: Tenant admin can list all platform tenants via /api/admin/tenants; owned by NR-1.1-A"
)
def test_probe_i01_tenant_admin_cannot_list_all_platform_tenants(nr0_scenario, isolated_db: Session):
    """
    Defect Assertion: Calling global get_admin_tenants with a Tenant Admin user
    MUST NOT return other tenants' information. Desired: 403 or only own tenant.
    """
    admin_u1 = nr0_scenario["users"]["u1_admin"]
    t1 = nr0_scenario["tenants"]["t1"]
    t2 = nr0_scenario["tenants"]["t2"]
    
    result = get_admin_tenants(current_user=admin_u1, db=isolated_db)
    
    # Desired safe behavior: Tenant admin must only receive their own tenant (or 403)
    returned_tenant_ids = [t["id"] for t in result]
    assert t2.id not in returned_tenant_ids, (
        f"Security Breach (I-01): Tenant Admin of Tenant {t1.id} received Tenant {t2.id} data!"
    )
    assert t1.id in returned_tenant_ids


# ===========================================================================
# 2. Family I-02: Widget Cross-Visitor / Private Chat Isolation (Owned by NR-1.1-B)
# ===========================================================================

def test_probe_i02_control_widget_generates_visitor_conversation(isolated_app, nr0_scenario):
    """Control: Normal widget session creation without conversation_id creates a new visitor conversation."""
    wk1 = nr0_scenario["widget_keys"]["wk1"]
    resp = isolated_app.post(
        "/api/widget/session",
        json={"public_key": wk1.public_key},
        headers={"Origin": "https://acme.com"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_token" in data or "token" in data
    assert data["conversation_id"] is not None


@pytest.mark.xfail(
    strict=True,
    reason="Issue I-02: Widget session allows adopting private dashboard chat; owned by NR-1.1-B"
)
def test_probe_i02_widget_cannot_adopt_private_dashboard_conversation(isolated_app, nr0_scenario):
    """
    Defect Assertion: Passing a private dashboard conversation ID to widget handshake
    MUST NOT bind to or disclose that private conversation.
    """
    wk1 = nr0_scenario["widget_keys"]["wk1"]
    private_conv = nr0_scenario["conversations"]["c1_analyst"] # Private to analyst
    
    resp = isolated_app.post(
        "/api/widget/session",
        json={"public_key": wk1.public_key, "conversation_id": private_conv.id},
        headers={"Origin": "https://acme.com"}
    )
    
    # Desired safe behavior: Anonymous widget visitor cannot adopt internal dashboard chat
    if resp.status_code == 200:
        data = resp.json()
        assert data["conversation_id"] != private_conv.id, (
            f"Security Breach (I-02): Widget session adopted private dashboard conversation {private_conv.id}!"
        )
    else:
        assert resp.status_code in (403, 404)


# ===========================================================================
# 3. Family I-08: SQL Engine Outer LIMIT Enforcement (Owned by NR-1.2-B)
# ===========================================================================

def test_probe_i08_control_sql_execution_basic(tmp_path):
    """Control: Basic query execution returns expected single row."""
    db_file = tmp_path / "control_db.sqlite"
    test_db_url = f"sqlite:///{db_file}"
    engine = create_engine(test_db_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE test_data (id INT, val INT);"))
        conn.execute(text("INSERT INTO test_data VALUES (1, 100);"))
        
    db_conn = models.DatabaseConnection(
        id=999,
        db_type="sqlite",
        connection_string=test_db_url
    )
    res = execute_safe_sql(db_conn, "SELECT * FROM test_data", max_rows=10, timeout_ceiling=2.0)
    assert res["row_count"] == 1


@pytest.mark.xfail(
    strict=True,
    reason="Issue I-08: Any existing LIMIT bypasses outer max_rows cap; owned by NR-1.2-B"
)
def test_probe_i08_sql_executor_enforces_max_rows_when_query_has_limit(tmp_path):
    """
    Defect Assertion: When a query includes its own LIMIT larger than max_rows,
    execute_safe_sql MUST enforce the caller's max_rows ceiling.
    """
    # Create an isolated SQLite table with 50 rows
    db_file = tmp_path / "numbers_db.sqlite"
    test_db_url = f"sqlite:///{db_file}"
    temp_engine = create_engine(test_db_url)
    with temp_engine.begin() as conn:
        conn.execute(text("CREATE TABLE numbers (n INT);"))
        for i in range(50):
            conn.execute(text(f"INSERT INTO numbers VALUES ({i});"))
            
    db_conn = models.DatabaseConnection(
        id=998,
        db_type="sqlite",
        connection_string=test_db_url
    )
    
    # Query contains 'LIMIT 50', but caller requests 'max_rows=5'
    query_with_limit = "SELECT * FROM numbers LIMIT 50"
    res = execute_safe_sql(db_conn, query_with_limit, max_rows=5, timeout_ceiling=2.0)
    
    # Desired safe behavior: Rows returned must NOT exceed max_rows (5)
    assert res["row_count"] <= 5, (
        f"Correctness Failure (I-08): execute_safe_sql returned {res['row_count']} rows; "
        f"exceeded max_rows=5 limit because inner LIMIT suppressed capping!"
    )


# ===========================================================================
# 4. Family I-11: Citation Grounding Failure Honesty (Owned by NR-2.2-A)
# ===========================================================================

def test_probe_i11_control_citation_service_empty_claims():
    """Control: CitationService returns ungrounded / zero confidence when no claims exist."""
    service = CitationService()
    res = service.verify_grounding(
        response_text="Hello, how can I help you today?",
        retrieved_chunks=[]
    )
    assert res["grounding_confidence"] == 0.0 or res["citations"] == []


@pytest.mark.xfail(
    strict=True,
    reason="Issue I-11: Embedding error returns positive 0.7 confidence without disclaimer; owned by NR-2.2-A"
)
def test_probe_i11_citation_grounding_reports_failure_honestly():
    """
    Defect Assertion: When embedding generation throws an exception, verify_grounding
    MUST NOT claim a positive grounding_confidence (0.7) or has_low_confidence=False.
    """
    service = CitationService()
    
    # Mock embedding model to raise an error
    faulty_embedder = MagicMock()
    faulty_embedder.embed_documents.side_effect = RuntimeError("Embedding service unavailable")
    
    chunks = [
        {"content": "Acme revenue was $10M in 2024.", "metadata": {"source": "report.pdf", "page_number": 1}}
    ]
    
    res = service.verify_grounding(
        answer="Acme reported revenue of $10M in fiscal year 2024.",
        retrieved_chunks=chunks,
        embedding_model=faulty_embedder
    )
    
    # Desired safe behavior: Failed grounding check must be ungrounded, not confidence 0.7
    assert res["has_low_confidence"] is True, (
        "Correctness Failure (I-11): verify_grounding claimed has_low_confidence=False during embedding failure!"
    )
    assert res["grounding_confidence"] <= 0.0 or res["disclaimer"] is not None, (
        f"Correctness Failure (I-11): returned reassuring confidence {res['grounding_confidence']} on failed check!"
    )


# ===========================================================================
# 5. Family I-14: Widget Double Generation (Owned by NR-2.3-A)
# ===========================================================================

@pytest.mark.xfail(
    strict=True,
    reason="Issue I-14: Widget non-streaming generates answer twice; owned by NR-2.3-A"
)
def test_probe_i14_widget_non_streaming_generates_answer_only_once(isolated_app, nr0_scenario):
    """
    Defect Assertion: A non-streaming widget chat request MUST generate the answer exactly once.
    Currently, lines 514/531 and line 635 of widget.py both invoke LLM generation.
    """
    wk1 = nr0_scenario["widget_keys"]["wk1"]
    
    # 1. Establish session
    session_resp = isolated_app.post(
        "/api/widget/session",
        json={"public_key": wk1.public_key},
        headers={"Origin": "https://acme.com"}
    )
    token = session_resp.json()["token"]
    
    generation_call_count = 0
    def fake_gemini_api(prompt, key):
        nonlocal generation_call_count
        generation_call_count += 1
        return "Synthetic response."
        
    with patch("routers.widget.call_gemini_api", side_effect=fake_gemini_api):
        chat_resp = isolated_app.post(
            "/api/chat/widget",
            json={"query": "Tell me about your business hours", "stream": False},
            headers={"Authorization": f"Bearer {token}", "Origin": "https://acme.com"}
        )
        assert chat_resp.status_code == 200
        
    # Desired behavior: Exactly 1 LLM generation invocation per request
    assert generation_call_count == 1, (
        f"Performance/Cost Defect (I-14): Expected 1 generation call, but observed {generation_call_count}!"
    )


# ===========================================================================
# 6. Family I-09: KPI Trend Formula Fidelity (Owned by NR-2.1-A)
# ===========================================================================

def test_probe_i09_control_kpi_total_sum():
    """Control: 10 rows of 100 revenue produce sum of 1000."""
    df = pd.DataFrame({"revenue": [100.0] * 10})
    assert df["revenue"].sum() == 1000.0


@pytest.mark.xfail(
    strict=True,
    reason="Issue I-09: KPI trend compares aggregate sum to row mean, inventing 900% growth; owned by NR-2.1-A"
)
def test_probe_i09_kpi_trend_does_not_compare_sum_to_mean():
    """
    Defect Assertion: 10 rows of 100 revenue (sum=1000, mean=100) MUST NOT compute
    a 900% growth trend by dividing aggregate sum by row mean (val - mean)/mean.
    """
    from services.automl_service import AutoMLPipeline
    pipeline = AutoMLPipeline()
    
    df = pd.DataFrame({"revenue": [100.0] * 10})
    profile = {
        "columns": {
            "revenue": {"mean": 100.0, "total": 1000.0}
        }
    }
    
    kpis = pipeline._generate_kpis(df, profile, source_type="database")
    revenue_kpi = next((k for k in kpis if k.get("column") == "revenue"), None)
    
    assert revenue_kpi is not None
    # Desired behavior: trend_pct must not be 900.0%
    assert revenue_kpi["trend_pct"] != 900.0, (
        "Correctness Failure (I-09): KPI trend compared total sum to single-row mean, inventing 900% growth!"
    )
