import os
import re
import requests
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool
import models
from services.sql_engine import get_connection_url

SQL_KEYWORDS = {
    "count", "how many", "total", "sum", "average", "avg", "min", "max", "top", "bottom",
    "group by", "order by", "table", "rows", "records", "database", "sql", "select",
    "highest", "lowest", "trend", "percentage", "rate", "dataset", "column"
}

RAG_KEYWORDS = {
    "document", "documents", "pdf", "file", "policy", "guideline", "manual", "contract",
    "clause", "section", "paragraph", "article", "report", "overview", "summarize",
    "summary", "what does", "according to", "explain the", "handbook", "procedure", "notes"
}

class QueryRouteDecision:
    def __init__(self, route_type: str, confidence: float, reasoning: str, database_id: Optional[int] = None):
        self.route_type = route_type # "rag" | "sql" | "hybrid"
        self.confidence = confidence
        self.reasoning = reasoning
        self.database_id = database_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route_type": self.route_type,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "database_id": self.database_id
        }


def auto_select_database(query: str, tenant_id: int, db: Session) -> Optional[models.DatabaseConnection]:
    """
    Intelligently select the best matching database connection for the tenant (Option C).
    Inspects connection names and table names against keywords in the query.
    """
    connections = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.tenant_id == tenant_id
    ).all()

    if not connections:
        return None

    if len(connections) == 1:
        return connections[0]

    q_lower = query.lower()

    # 1. Match by DB name
    for conn in connections:
        if conn.name.lower() in q_lower or conn.database.lower() in q_lower:
            return conn

    # 2. Match by introspected table names
    best_conn = connections[0]
    best_score = 0

    for conn in connections:
        conn_url = get_connection_url(conn)
        if not conn_url:
            continue
        try:
            engine = create_engine(conn_url, poolclass=NullPool)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            engine.dispose()
            
            score = sum(1 for t in tables if t.lower() in q_lower)
            if score > best_score:
                best_score = score
                best_conn = conn
        except Exception:
            continue

    return best_conn


def classify_query_route(
    query: str,
    tenant_id: int,
    db: Session,
    source_preference: Optional[str] = "auto",
    explicit_database_id: Optional[int] = None
) -> QueryRouteDecision:
    """
    Classifies whether the user query should route to RAG (document search),
    SQL (relational database), or Hybrid retrieval.
    """
    # 1. User manual override
    if source_preference == "documents":
        return QueryRouteDecision("rag", 1.0, "Manual user preference: Documents (RAG)")
    
    if source_preference == "database":
        db_conn = None
        if explicit_database_id:
            db_conn = db.query(models.DatabaseConnection).filter(
                models.DatabaseConnection.id == explicit_database_id,
                models.DatabaseConnection.tenant_id == tenant_id
            ).first()
        if not db_conn:
            db_conn = auto_select_database(query, tenant_id, db)
        return QueryRouteDecision(
            "sql", 1.0, "Manual user preference: Database (SQL)",
            database_id=db_conn.id if db_conn else None
        )

    # Check available tenant assets
    doc_count = db.query(models.Document).filter(
        models.Document.tenant_id == tenant_id,
        models.Document.status == "Completed"
    ).count()

    db_connections = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.tenant_id == tenant_id
    ).all()

    # If tenant has only docs and no DBs
    if doc_count > 0 and len(db_connections) == 0:
        return QueryRouteDecision("rag", 0.95, "Tenant has only indexed documents available.")

    # If tenant has only DBs and no docs
    if len(db_connections) > 0 and doc_count == 0:
        selected_db = auto_select_database(query, tenant_id, db)
        return QueryRouteDecision(
            "sql", 0.95, "Tenant has only connected databases available.",
            database_id=selected_db.id if selected_db else None
        )

    # If neither exists
    if doc_count == 0 and len(db_connections) == 0:
        return QueryRouteDecision("rag", 0.5, "No documents or databases configured for tenant.")

    # 2. Fast Keyword Heuristics
    q_lower = query.lower()
    sql_score = sum(1 for kw in SQL_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', q_lower))
    rag_score = sum(1 for kw in RAG_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', q_lower))

    # Check if query matches table names in tenant databases
    selected_db = auto_select_database(query, tenant_id, db)
    if selected_db:
        conn_url = get_connection_url(selected_db)
        if conn_url:
            try:
                engine = create_engine(conn_url, poolclass=NullPool)
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                engine.dispose()
                for table in tables:
                    if table.lower() in q_lower:
                        sql_score += 2
            except Exception:
                pass

    if sql_score >= 2 and rag_score == 0:
        return QueryRouteDecision("sql", 0.85, f"SQL heuristic matched (score: {sql_score})", database_id=selected_db.id if selected_db else None)

    if rag_score >= 2 and sql_score == 0:
        return QueryRouteDecision("rag", 0.85, f"RAG heuristic matched (score: {rag_score})")

    # 3. LLM Intent Classifier Fallback (Gemini Flash)
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        try:
            prompt = (
                "You are an intent classification engine for a hybrid SaaS platform.\n"
                "Determine whether the user query is best answered by:\n"
                "- 'SQL': querying structured relational database tables (numerical aggregates, filters, transactional records, counting, lists of users/orders/products).\n"
                "- 'RAG': searching unstructured knowledge base documents (PDFs, policies, explanations, summaries, text passages, contracts, reports).\n"
                "- 'HYBRID': requiring both structured SQL data and document context.\n\n"
                f"User Query: {query}\n\n"
                "Respond with EXACTLY one word: 'SQL', 'RAG', or 'HYBRID'."
            )
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {"Content-Type": "application/json"}
            res = requests.post(gemini_url, json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                res_data = res.json()
                raw_decision = res_data["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
                if "SQL" in raw_decision:
                    return QueryRouteDecision("sql", 0.9, "LLM classifier routed to SQL", database_id=selected_db.id if selected_db else None)
                elif "RAG" in raw_decision:
                    return QueryRouteDecision("rag", 0.9, "LLM classifier routed to RAG")
                elif "HYBRID" in raw_decision:
                    return QueryRouteDecision("hybrid", 0.85, "LLM classifier routed to Hybrid", database_id=selected_db.id if selected_db else None)
        except Exception as e:
            print(f"LLM classifier exception: {e}")

    # Default fallback based on highest score or RAG default
    if sql_score > rag_score:
        return QueryRouteDecision("sql", 0.7, "Heuristic majority to SQL", database_id=selected_db.id if selected_db else None)
    return QueryRouteDecision("rag", 0.7, "Default fallback to RAG Knowledge Base")
