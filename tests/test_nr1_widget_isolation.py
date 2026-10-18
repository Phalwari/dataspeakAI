"""
DataSpeakAI — Sprint NR-1.1-B: Widget Visitor Isolation & Continuity Tests
Verifies:
- NR-1.1-B-T01: Cryptographic session claims bound to (tenant_id, widget_key_id, visitor_id, conversation_id).
- NR-1.1-B-T02: Anonymous visitor conversation generation and continuity token resumption.
- NR-1.1-B-T03: Prevention of conversation switching in /api/widget/chat (Defect I-02).
- NR-1.1-B-T04: Pre-allocation token bucket rate limiting on /api/widget/session.
"""
import pytest
import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import models
from services.widget_session_service import get_widget_hmac_secret, create_widget_continuity_token


def test_session_token_binding(isolated_app: TestClient, nr0_scenario):
    """
    NR-1.1-B-T01: Ensure session token cryptographically binds tenant_id, widget_key_id, visitor_id, conversation_id.
    Tampering with claims triggers 401.
    """
    wk1 = nr0_scenario["widget_keys"]["wk1"]
    resp = isolated_app.post(
        "/api/widget/session",
        json={"public_key": wk1.public_key},
        headers={"Origin": "https://acme.com"}
    )
    assert resp.status_code == 200
    data = resp.json()
    token = data["session_token"]
    assert "visitor_id" in data and len(data["visitor_id"]) > 0
    assert "continuity_token" in data and len(data["continuity_token"]) > 0

    # Inspect decoded payload
    secret = get_widget_hmac_secret()
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    assert payload["sub"] == "widget_session"
    assert payload["tenant_id"] == wk1.tenant_id
    assert payload["widget_key_id"] == wk1.id
    assert payload["public_key"] == wk1.public_key
    assert payload["conversation_id"] == data["conversation_id"]
    assert payload["visitor_id"] == data["visitor_id"]

    # Tampered token: modified tenant_id with invalid signature
    tampered_token = token[:-5] + "XXXXX"
    chat_resp = isolated_app.post(
        "/api/widget/chat",
        json={"session_token": tampered_token, "query": "hello"},
        headers={"Origin": "https://acme.com"}
    )
    assert chat_resp.status_code == 401


def test_visitor_conversation_continuity(isolated_app: TestClient, nr0_scenario, isolated_db: Session):
    """
    NR-1.1-B-T02: Fresh visitor gets new conversation.
    Resumption succeeds with valid continuity token.
    Resumption without continuity token safely generates new conversation instead of adopting.
    """
    wk1 = nr0_scenario["widget_keys"]["wk1"]
    
    # 1. Fresh visitor handshake
    resp1 = isolated_app.post(
        "/api/widget/session",
        json={"public_key": wk1.public_key},
        headers={"Origin": "https://acme.com"}
    )
    assert resp1.status_code == 200
    d1 = resp1.json()
    conv1_id = d1["conversation_id"]
    visitor_id = d1["visitor_id"]
    continuity_token = d1["continuity_token"]

    # 2. Resumption with valid continuity proof -> same conversation
    resp2 = isolated_app.post(
        "/api/widget/session",
        json={
            "public_key": wk1.public_key,
            "conversation_id": conv1_id,
            "visitor_id": visitor_id,
            "continuity_token": continuity_token
        },
        headers={"Origin": "https://acme.com"}
    )
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["conversation_id"] == conv1_id
    assert d2["visitor_id"] == visitor_id

    # 3. Attempting to resume with an invalid/forged continuity token -> starts fresh conversation
    bad_token = continuity_token[:-6] + "BADTOK"
    resp3 = isolated_app.post(
        "/api/widget/session",
        json={
            "public_key": wk1.public_key,
            "conversation_id": conv1_id,
            "visitor_id": visitor_id,
            "continuity_token": bad_token
        },
        headers={"Origin": "https://acme.com"}
    )
    assert resp3.status_code == 200
    d3 = resp3.json()
    assert d3["conversation_id"] != conv1_id, "Must not adopt conversation with invalid continuity token"


def test_widget_cannot_adopt_dashboard_conversation_with_forged_proof(isolated_app: TestClient, nr0_scenario):
    """
    NR-1.1-B-T02 / I-02: Even if an attacker generates a token pointing to a dashboard conversation,
    the server only resumes conversations where platform == 'widget'.
    """
    wk1 = nr0_scenario["widget_keys"]["wk1"]
    private_conv = nr0_scenario["conversations"]["c1_analyst"] # platform="web"

    # Attacker crafts continuity token pointing to private dashboard conv
    forged_token = create_widget_continuity_token(
        tenant_id=wk1.tenant_id,
        widget_key_id=wk1.id,
        public_key=wk1.public_key,
        visitor_id="attacker_123",
        conversation_id=private_conv.id
    )

    resp = isolated_app.post(
        "/api/widget/session",
        json={
            "public_key": wk1.public_key,
            "conversation_id": private_conv.id,
            "continuity_token": forged_token
        },
        headers={"Origin": "https://acme.com"}
    )
    assert resp.status_code == 200
    d = resp.json()
    assert d["conversation_id"] != private_conv.id, "Must never adopt a web/dashboard conversation into widget"


def test_chat_conversation_switching_prevented(isolated_app: TestClient, nr0_scenario, isolated_db: Session):
    """
    NR-1.1-B-T03: Request-body conversation_id mismatching session token claims is rejected with 403.
    """
    wk1 = nr0_scenario["widget_keys"]["wk1"]

    # Session 1
    resp1 = isolated_app.post(
        "/api/widget/session",
        json={"public_key": wk1.public_key},
        headers={"Origin": "https://acme.com"}
    )
    assert resp1.status_code == 200
    s1 = resp1.json()

    # Session 2
    resp2 = isolated_app.post(
        "/api/widget/session",
        json={"public_key": wk1.public_key},
        headers={"Origin": "https://acme.com"}
    )
    assert resp2.status_code == 200
    s2 = resp2.json()

    # Visitor from Session 1 attempts to inject messages into Session 2 conversation
    chat_resp = isolated_app.post(
        "/api/widget/chat",
        json={
            "session_token": s1["session_token"],
            "conversation_id": s2["conversation_id"], # Mismatch!
            "query": "hello attacker"
        },
        headers={"Origin": "https://acme.com"}
    )
    assert chat_resp.status_code == 403
    assert "mismatch" in chat_resp.json()["detail"].lower()


def test_session_handshake_rate_limiter(isolated_app: TestClient, nr0_scenario):
    """
    NR-1.1-B-T04: Rapid session handshakes trigger HTTP 429 Too Many Requests before DB allocation.
    """
    wk1 = nr0_scenario["widget_keys"]["wk1"]

    # Exhaust the rate limit by firing multiple rapid handshake requests
    hit_429 = False
    for _ in range(40):
        resp = isolated_app.post(
            "/api/widget/session",
            json={"public_key": wk1.public_key},
            headers={"Origin": "https://acme.com"}
        )
        if resp.status_code == 429:
            hit_429 = True
            assert "Retry-After" in resp.headers
            break

    assert hit_429, "Expected rate limit 429 response when exceeding handshake threshold"


def test_widget_key_documents(isolated_app: TestClient, nr0_scenario, isolated_db: Session):
    """
    NR-1.1-B-T05: Tenant admin can assign and unpublish documents to widget keys; foreign tenant documents rejected.
    """
    admin_u1 = nr0_scenario["users"]["u1_admin"]
    t1 = nr0_scenario["tenants"]["t1"]
    t2 = nr0_scenario["tenants"]["t2"]
    wk1 = nr0_scenario["widget_keys"]["wk1"]

    from auth import create_access_token
    token = create_access_token({"sub": admin_u1.email, "tv": admin_u1.token_version, "tenant_id": t1.id})
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Create document in Tenant 1 and Tenant 2
    d1 = models.Document(
        tenant_id=t1.id,
        name="tenant1_doc.pdf",
        file_type="PDF",
        size=1024,
        status="Completed"
    )
    d2_foreign = models.Document(
        tenant_id=t2.id,
        name="tenant2_secret.pdf",
        file_type="PDF",
        size=2048,
        status="Completed"
    )
    isolated_db.add_all([d1, d2_foreign])
    isolated_db.commit()
    isolated_db.refresh(d1)
    isolated_db.refresh(d2_foreign)

    # 2. Get published documents (initially empty)
    get_res = isolated_app.get(f"/api/keys/widget/{wk1.id}/documents", headers=auth_headers)
    assert get_res.status_code == 200
    assert d1.id not in get_res.json()["published_document_ids"]

    # 3. Assign foreign tenant document -> HTTP 400
    bad_assign = isolated_app.post(
        f"/api/keys/widget/{wk1.id}/documents",
        json={"document_ids": [d2_foreign.id]},
        headers=auth_headers
    )
    assert bad_assign.status_code == 400
    assert "does not belong" in bad_assign.json()["detail"].lower()

    # 4. Assign valid tenant 1 document -> HTTP 200 (both plural and singular payload)
    good_assign = isolated_app.post(
        f"/api/keys/widget/{wk1.id}/documents",
        json={"document_ids": [d1.id]},
        headers=auth_headers
    )
    assert good_assign.status_code == 200
    assert d1.id in good_assign.json()["published_document_ids"]

    # 5. Unpublish document -> HTTP 200
    del_res = isolated_app.delete(f"/api/keys/widget/{wk1.id}/documents/{d1.id}", headers=auth_headers)
    assert del_res.status_code == 200

    # 6. Verify empty again
    get_res2 = isolated_app.get(f"/api/keys/widget/{wk1.id}/documents", headers=auth_headers)
    assert get_res2.status_code == 200
    assert d1.id not in get_res2.json()["published_document_ids"]

    # 7. Test singular document_id payload -> HTTP 200
    good_assign_singular = isolated_app.post(
        f"/api/keys/widget/{wk1.id}/documents",
        json={"document_id": d1.id},
        headers=auth_headers
    )
    assert good_assign_singular.status_code == 200
    assert d1.id in good_assign_singular.json()["published_document_ids"]

    # 8. Test bulk unpublish endpoint -> HTTP 200
    bulk_del_res = isolated_app.delete(f"/api/keys/widget/{wk1.id}/documents", headers=auth_headers)
    assert bulk_del_res.status_code == 200
    get_res3 = isolated_app.get(f"/api/keys/widget/{wk1.id}/documents", headers=auth_headers)
    assert get_res3.status_code == 200
    assert len(get_res3.json()["published_document_ids"]) == 0


def test_widget_rag_publication_filter(isolated_db: Session):
    """
    NR-1.1-B-T06: retrieve_rag_chunks strictly filters out unpublished and incomplete documents.
    """
    from routers.chat import retrieve_rag_chunks

    # Create two documents
    doc_pub = models.Document(tenant_id=1, name="Public.pdf", file_type="PDF", size=100, status="Completed")
    doc_priv = models.Document(tenant_id=1, name="Private.pdf", file_type="PDF", size=100, status="Completed")
    doc_failed = models.Document(tenant_id=1, name="Failed.pdf", file_type="PDF", size=100, status="Failed")
    isolated_db.add_all([doc_pub, doc_priv, doc_failed])
    isolated_db.commit()
    isolated_db.refresh(doc_pub)
    isolated_db.refresh(doc_priv)
    isolated_db.refresh(doc_failed)

    # Chunks
    c_pub = models.DocumentChunk(document_id=doc_pub.id, content="Public content alpha", chunk_index=0)
    c_priv = models.DocumentChunk(document_id=doc_priv.id, content="Private payroll secret", chunk_index=0)
    c_failed = models.DocumentChunk(document_id=doc_failed.id, content="Incomplete chunk", chunk_index=0)
    isolated_db.add_all([c_pub, c_priv, c_failed])
    isolated_db.commit()
    isolated_db.refresh(c_pub)
    isolated_db.refresh(c_priv)
    isolated_db.refresh(c_failed)

    # When allowed_document_ids={doc_pub.id}, only doc_pub is allowed
    from unittest.mock import patch, MagicMock
    import numpy as np

    mock_candidates = [
        {"content": c_pub.content, "metadata": {"chunk_id": c_pub.id, "document_id": doc_pub.id}, "score": 0.9},
        {"content": c_priv.content, "metadata": {"chunk_id": c_priv.id, "document_id": doc_priv.id}, "score": 0.8},
        {"content": c_failed.content, "metadata": {"chunk_id": c_failed.id, "document_id": doc_failed.id}, "score": 0.7},
    ]

    mock_vectorstore = MagicMock()
    mock_vectorstore.index.d = 384
    mock_vectorstore.index.search.return_value = (np.array([[]]), np.array([[]]))
    mock_vectorstore.index_to_docstore_id = {}
    mock_vectorstore.docstore._dict = {}

    mock_emb = MagicMock()
    mock_emb.embed_query.return_value = [0.1] * 384

    with patch("routers.documents.resolve_tenant_vector_index_path", return_value=("fake_path", True)), \
         patch("os.path.exists", return_value=True), \
         patch("langchain_community.vectorstores.FAISS.load_local", return_value=mock_vectorstore), \
         patch("routers.chat.get_embeddings", return_value=mock_emb), \
         patch("routers.chat.reciprocal_rank_fusion", return_value=mock_candidates), \
         patch("routers.chat.cross_encoder_rerank", side_effect=lambda q, hits, top_k: hits):

        results = retrieve_rag_chunks(
            query="test",
            tenant_id=1,
            db=isolated_db,
            top_k=5,
            allowed_document_ids={doc_pub.id}
        )

        # Assert: ONLY doc_pub passed validation; doc_priv was filtered by publication, doc_failed by status != Completed
        res_chunk_ids = [r["metadata"]["chunk_id"] for r in results]
        assert c_pub.id in res_chunk_ids
        assert c_priv.id not in res_chunk_ids, "Unpublished document must be filtered out!"
        assert c_failed.id not in res_chunk_ids, "Non-completed document status must be filtered out!"


def test_widget_sql_table_grants(isolated_app: TestClient, nr0_scenario, isolated_db: Session):
    """
    NR-1.1-B-T07: Disallowed SQL operations return clean non-leaking messages without executing SQL.
    Restricted tables outside allowed_tables are blocked.
    """
    wk1 = nr0_scenario["widget_keys"]["wk1"]
    wk1.allow_sql = False
    isolated_db.commit()

    # 1. Establish session
    s_resp = isolated_app.post(
        "/api/widget/session",
        json={"public_key": wk1.public_key},
        headers={"Origin": "https://acme.com"}
    )
    assert s_resp.status_code == 200
    token = s_resp.json()["session_token"]

    # 2. When allow_sql=False, requesting database tables returns safe response
    chat_resp = isolated_app.post(
        "/api/widget/chat",
        json={"session_token": token, "query": "select * from database users table"},
        headers={"Origin": "https://acme.com"}
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert "disabled" in data["answer"].lower()

    # 3. Now enable allow_sql with restricted table allowlist: ["products"]
    wk1.allow_sql = True
    wk1.allowed_database_ids = [999]
    wk1.allowed_tables = ["products"]
    isolated_db.commit()

    # Re-handshake
    s_resp2 = isolated_app.post(
        "/api/widget/session",
        json={"public_key": wk1.public_key},
        headers={"Origin": "https://acme.com"}
    )
    token2 = s_resp2.json()["session_token"]

    from unittest.mock import patch
    fake_db_conn = models.DatabaseConnection(id=999, tenant_id=wk1.tenant_id, name="TestDB", db_type="sqlite")
    isolated_db.add(fake_db_conn)
    isolated_db.commit()

    # If the user tries to query unauthorized table 'users':
    with patch("routers.widget.generate_sql_from_nl", return_value={"sql": "SELECT * FROM users", "explanation": "users query"}):
        chat_resp2 = isolated_app.post(
            "/api/widget/chat",
            json={"session_token": token2, "query": "show me all users in database table"},
            headers={"Origin": "https://acme.com"}
        )
        assert chat_resp2.status_code == 200
        ans2 = chat_resp2.json()["answer"]
        assert "not permitted" in ans2.lower()

    # 4. Streamed verification (Finding F02): When query is unauthorized, stream delivers error and terminates
    with patch("routers.widget.generate_sql_from_nl", return_value={"sql": "SELECT * FROM users", "explanation": "users query"}):
        stream_resp = isolated_app.post(
            "/api/widget/chat",
            json={"session_token": token2, "query": "show me all users in database table", "stream": True},
            headers={"Origin": "https://acme.com"}
        )
        assert stream_resp.status_code == 200
        stream_text = stream_resp.text
        assert "not permitted" in stream_text.lower() or "restricted" in stream_text.lower()
        assert '"done": true' in stream_text.lower()

