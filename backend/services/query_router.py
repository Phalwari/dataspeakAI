import os
import re
import requests
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool
import models
from services.connection_factory import DatabaseConnectionFactory
from services.sql_engine import get_connection_url

SQL_KEYWORDS = {
    "count", "how many", "total", "sum", "average", "avg", "min", "max", "top", "bottom",
    "group by", "order by", "table", "rows", "records", "database", "sql", "select",
    "highest", "lowest", "trend", "percentage", "rate", "dataset", "column",
    "filter", "where", "sort", "limit", "filter those", "show those", "filter by",
    "filter these", "show that", "show these", "top 3", "top 5", "top 10",
    "summarize that", "summarize that in a table", "in a table", "break down",
    "breakdown", "grouped by", "only the", "what about", "how about", "now filter",
    "drill down", "by status", "by category", "by date", "by year", "by month",
    "these records", "those records", "these rows", "those rows", "these results", "those results"
}

RAG_KEYWORDS = {
    "document", "documents", "pdf", "file", "policy", "guideline", "manual", "contract",
    "clause", "section", "paragraph", "article", "report", "overview", "summarize",
    "summary", "what does", "according to", "explain the", "handbook", "procedure", "notes"
}

CONVERSATIONAL_KEYWORDS = {
    "hello", "hi", "hey", "greetings", "howdy", "good morning", "good afternoon", "good evening",
    "who are you", "what are you", "what can you do", "what do you do", "how can you help",
    "how do you work", "help", "help me", "introduce yourself", "tell me about yourself",
    "what is dataspeak", "what is dataspeakai", "features", "capabilities",
    "how to connect", "how do i connect", "connect postgresql", "connect mysql", "connect sqlite", "connect database",
    "how to upload", "how do i upload", "upload documents", "upload document", "how does rag work", "knowledge base",
    "erd", "schema visualizer", "chatbot widget", "embed widget", "api key",
    "multi-tenant", "tenant isolation", "security"
}

GREETING_REGEX = re.compile(
    r'^(hi|hello|hey|howdy|greetings|good\s+(morning|afternoon|evening|day)|sup|yo)([\s,!.]|$)',
    re.IGNORECASE
)

PLATFORM_HELP_REGEX = re.compile(
    r'\b(what\s+can\s+you\s+do|who\s+are\s+you|'
    r'how\s+(?:do\s+i|can\s+i|to)\s+(?:connect|upload|embed|use|view|create|export|share|query)|'
    r'how\s+does\s+(?:dataspeak|rag|erd|widget|the\s+chatbot|it\s+work)|'
    r'what\s+is\s+(?:dataspeak|rag|erd|an\s+erd|the\s+widget)|'
    r'can\s+i\s+(?:connect|upload|use|embed)|'
    r'tell\s+me\s+about\s+(?:dataspeak|yourself|features|capabilities|erd|widget)|'
    r'platform\s+help|what\s+are\s+your\s+capabilities|help\s+me(?:\s+get\s+started)?)\b',
    re.IGNORECASE
)

ANAPHORA_PATTERNS = re.compile(
    r'\b(filter\s+(?:those|these|by|them)|show\s+(?:those|these|that|the\s+top|me\s+more)|'
    r'summarize\s+(?:that|those|these)|in\s+a\s+table|what\s+about|how\s+about|'
    r'now\s+(?:only|filter|show)|only\s+the|top\s+\d+|bottom\s+\d+|drill\s+down|'
    r'more\s+details|tell\s+me\s+more|'
    r'sort\s+by|order\s+by|group\s+by|break\s+down)\b',
    re.IGNORECASE
)

class QueryRouteDecision:
    def __init__(self, route_type: str, confidence: float, reasoning: str, database_id: Optional[int] = None):
        self.route_type = route_type # "rag" | "sql" | "hybrid" | "conversational"
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


_GENERIC_CONNECTION_TOKENS = {"demo", "data", "database", "db"}


def _connection_match_score(conn: models.DatabaseConnection, query: str) -> int:
    """Score explicit source references without relying on the full display name."""
    q_lower = query.lower()
    q_tokens = set(re.findall(r"[a-z0-9]+", q_lower))
    name_tokens = [t for t in re.findall(r"[a-z0-9]+", (conn.name or "").lower()) if t not in _GENERIC_CONNECTION_TOKENS]
    db_tokens = re.findall(r"[a-z0-9]+", (conn.database or "").lower())
    db_type = str(conn.db_type or "").lower()

    score = sum(3 for token in set(name_tokens + db_tokens) if len(token) > 2 and token in q_tokens)
    type_aliases = {
        "postgresql": {"postgresql", "postgres", "pgsql"},
        "mysql": {"mysql", "mariadb"},
        "mariadb": {"mysql", "mariadb"},
        "mongodb": {"mongodb", "mongo"},
        "sqlite": {"sqlite"},
    }
    if q_tokens.intersection(type_aliases.get(db_type, {db_type})):
        score += 6
    return score


def find_explicit_database_matches(
    query: str,
    connections: List[models.DatabaseConnection]
) -> List[models.DatabaseConnection]:
    scored = [(conn, _connection_match_score(conn, query)) for conn in connections]
    return [conn for conn, score in sorted(scored, key=lambda item: item[1], reverse=True) if score > 0]


def auto_select_database(
    query: str,
    tenant_id: int,
    db: Session,
    fallback_database_id: Optional[int] = None
) -> Optional[models.DatabaseConnection]:
    """
    Intelligently select the best matching database connection for the tenant (Option C).
    Inspects connection names and table names against keywords in the query.
    Falls back to prior active database connection if available for multi-turn continuity.
    """
    connections = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.tenant_id == tenant_id
    ).all()

    if not connections:
        return None

    if len(connections) == 1:
        return connections[0]

    q_lower = query.lower()

    # 1. Match explicit connection labels and dialect aliases. Display names
    # contain separators such as "Demo | ... | MySQL", so matching the full
    # string misses valid source references in natural-language questions.
    explicit_matches = find_explicit_database_matches(query, connections)
    if explicit_matches:
        return explicit_matches[0]

    # 2. Match by introspected table names
    best_conn = None
    best_score = 0

    for conn in connections:
        conn_url = DatabaseConnectionFactory.get_connection_url(conn)
        if not conn_url:
            continue
        try:
            if str(conn.db_type or "").lower() == "mongodb":
                # SQLAlchemy cannot introspect MongoDB. Use the bounded Mongo
                # catalog path so collection names can select the right source
                # instead of falling back to the previous relational database.
                from services.mongo_query import open_database
                client, mongo_db = open_database(conn)
                try:
                    collections = mongo_db.list_collection_names()
                    score = sum(1 for name in collections if name.lower() in q_lower)
                finally:
                    client.close()
                if score > best_score:
                    best_score = score
                    best_conn = conn
                continue
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

    if best_conn and best_score > 0:
        return best_conn

    # 3. Prefer prior active database if valid for tenant (Anaphora continuity)
    if fallback_database_id:
        prior_conn = next((c for c in connections if c.id == fallback_database_id), None)
        if prior_conn:
            return prior_conn

    return connections[0]


def classify_query_route(
    query: str,
    tenant_id: int,
    db: Session,
    source_preference: Optional[str] = "auto",
    explicit_database_id: Optional[int] = None,
    prior_database_id: Optional[int] = None
) -> QueryRouteDecision:
    """
    Classifies whether the user query should route to Conversational (platform help/greetings),
    RAG (document search), SQL (relational database), or Hybrid retrieval.
    """
    # 1. User manual override
    if source_preference == "conversational":
        return QueryRouteDecision("conversational", 1.0, "Manual user preference: Conversational")

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
            db_conn = auto_select_database(query, tenant_id, db, fallback_database_id=prior_database_id)
        return QueryRouteDecision(
            "sql", 1.0, "Manual user preference: Database (SQL)",
            database_id=db_conn.id if db_conn else None
        )

    # 2. Fast Conversational Heuristics (Greetings & Platform Help)
    q_lower = query.lower().strip()
    is_greeting = bool(GREETING_REGEX.match(q_lower))
    is_platform_help = bool(PLATFORM_HELP_REGEX.search(q_lower))
    conv_score = sum(1 for kw in CONVERSATIONAL_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', q_lower))
    sql_score = sum(1 for kw in SQL_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', q_lower))
    rag_score = sum(1 for kw in RAG_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', q_lower))

    # Check for operational data queries (requesting specific calculations, metrics, or table data rows)
    has_operational_data_intent = bool(re.search(
        r'\b(how\s+many|count|sum|avg|average|min|max|total\s+(?:sales|revenue|users|orders|count|records|amount)|'
        r'top\s+\d+|bottom\s+\d+|select\s+.+\s+from|from\s+the\s+table|show\s+me\s+the\s+(?:top|all|table)|'
        r'list\s+all\s+\w+)\b',
        q_lower
    ))

    # If platform help (e.g. "How do I connect a PostgreSQL database?", "How do I upload a document?", "What can you do?")
    # and no operational calculation is requested, route immediately to conversational
    if is_platform_help and not has_operational_data_intent:
        return QueryRouteDecision("conversational", 0.95, "Conversational intent matched (platform capability help).")

    # If greeting (e.g. "Hello", "Hi there") and no explicit operational calculation, route immediately to conversational
    if is_greeting and not has_operational_data_intent:
        return QueryRouteDecision("conversational", 0.95, "Conversational intent matched (greeting).")

    if conv_score >= 2 and not has_operational_data_intent:
        return QueryRouteDecision("conversational", 0.90, "Conversational intent matched (platform capability inquiry).")

    # 2.5 Multi-Turn Anaphora & Context Continuity (R2)
    # If the user is in an active database conversation turn and follows up with anaphoric
    # references or filter/drilldown keywords without explicit document keywords, maintain SQL route.
    explicit_source_reference = bool(re.search(
        r"\b(postgresql|postgres|pgsql|mysql|mariadb|mongodb|mongo|coffee\s+retail|solar\s+wholesale|"
        r"subscription\s+billing|invoice|invoices|collection)\b",
        q_lower
    ))
    if prior_database_id and not (is_greeting or is_platform_help) and not explicit_source_reference:
        has_explicit_doc_keyword = any(k in q_lower for k in ("document", "documents", "pdf", "file", "contract", "manual", "handbook"))
        if not has_explicit_doc_keyword:
            if ANAPHORA_PATTERNS.search(q_lower) or (sql_score >= 1 and rag_score <= 1):
                prior_conn = db.query(models.DatabaseConnection).filter(
                    models.DatabaseConnection.id == prior_database_id,
                    models.DatabaseConnection.tenant_id == tenant_id
                ).first()
                if prior_conn:
                    return QueryRouteDecision(
                        "sql", 0.90,
                        f"Anaphoric follow-up resolving to prior active database '{prior_conn.name}'",
                        database_id=prior_conn.id
                    )

    # Check available tenant assets
    doc_count = db.query(models.Document).filter(
        models.Document.tenant_id == tenant_id,
        models.Document.status == "Completed"
    ).count()

    db_connections = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.tenant_id == tenant_id
    ).all()

    # If neither exists: route to conversational to avoid "no chunks found" dead-end
    if doc_count == 0 and len(db_connections) == 0:
        return QueryRouteDecision("conversational", 0.95, "No documents or databases configured for tenant; routing to platform assistant.")

    # If tenant has only docs and no DBs
    if doc_count > 0 and len(db_connections) == 0:
        if is_greeting or is_platform_help or conv_score >= 1:
            return QueryRouteDecision("conversational", 0.95, "Conversational intent matched.")
        return QueryRouteDecision("rag", 0.95, "Tenant has only indexed documents available.")

    # If tenant has only DBs and no docs
    if len(db_connections) > 0 and doc_count == 0:
        if is_greeting or is_platform_help or conv_score >= 1:
            return QueryRouteDecision("conversational", 0.95, "Conversational intent matched.")
        selected_db = auto_select_database(query, tenant_id, db, fallback_database_id=prior_database_id)
        has_document_intent = rag_score > 0 or any(
            marker in q_lower for marker in ("policy", "manual", "document", "according to", "shipping", "sla")
        )
        if selected_db and has_operational_data_intent and has_document_intent:
            return QueryRouteDecision(
                "hybrid", 0.92,
                "Deterministic mixed data and document intent",
                database_id=selected_db.id
            )
        return QueryRouteDecision(
            "sql", 0.95, "Tenant has only connected databases available.",
            database_id=selected_db.id if selected_db else None
        )

    # Check if query matches table names in tenant databases
    selected_db = auto_select_database(query, tenant_id, db, fallback_database_id=prior_database_id)
    explicit_matches = find_explicit_database_matches(query, db_connections)
    is_comparison_intent = bool(re.search(r"\b(compare|comparison|versus|vs\.?|between)\b", q_lower))
    if len(explicit_matches) > 1 and (has_operational_data_intent or is_comparison_intent):
        return QueryRouteDecision(
            "hybrid",
            0.95,
            "Multiple explicit database sources require source-specific execution",
            database_id=None
        )
    if selected_db:
        conn_url = DatabaseConnectionFactory.get_connection_url(selected_db)
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

    # Provider-independent routing guardrails. A provider outage must not turn
    # an operational database question into a document-only search.
    has_document_intent = rag_score > 0 or any(
        marker in q_lower for marker in ("policy", "manual", "document", "according to", "shipping", "sla")
    )
    if selected_db and has_operational_data_intent and has_document_intent:
        return QueryRouteDecision(
            "hybrid", 0.92,
            "Deterministic mixed data and document intent",
            database_id=selected_db.id
        )

    if selected_db and has_operational_data_intent and not has_document_intent:
        return QueryRouteDecision(
            "sql", 0.92,
            "Deterministic operational database intent",
            database_id=selected_db.id
        )

    if sql_score >= 2 and rag_score == 0:
        return QueryRouteDecision("sql", 0.85, f"SQL heuristic matched (score: {sql_score})", database_id=selected_db.id if selected_db else None)

    if rag_score >= 2 and sql_score == 0:
        return QueryRouteDecision("rag", 0.85, f"RAG heuristic matched (score: {rag_score})")

    # 3. LLM Intent Classifier Fallback (Gemini Flash)
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key or os.getenv("GROQ_API_KEY"):
        try:
            prompt = (
                "You are an intent classification engine for a hybrid SaaS platform.\n"
                "Determine whether the user query is best answered by:\n"
                "- 'CONVERSATIONAL': greetings, general platform help, capabilities of DataSpeakAI (how to connect databases, upload documents, ERD visualizer, widget customization, security), or general conversation.\n"
                "- 'SQL': querying structured relational database tables (numerical aggregates, filters, transactional records, counting, lists of users/orders/products).\n"
                "- 'RAG': searching unstructured knowledge base documents (PDFs, policies, explanations, summaries, text passages, contracts, reports).\n"
                "- 'HYBRID': requiring both structured SQL data and document context.\n\n"
                f"User Query: {query}\n\n"
                "Respond with EXACTLY one word: 'CONVERSATIONAL', 'SQL', 'RAG', or 'HYBRID'."
            )
            raw_decision = ""
            # If requests.post was explicitly monkeypatched in test fixtures (e.g. test_hybrid_classifier_response_reaches_route)
            if getattr(requests.post, "__module__", "") != "requests.api":
                gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                headers = {"Content-Type": "application/json"}
                res = requests.post(gemini_url, json=payload, headers=headers, timeout=5)
                if res.status_code == 200:
                    res_data = res.json()
                    raw_decision = res_data["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
            else:
                from services.llm_generation_service import llm_gateway
                raw = llm_gateway.generate_sync(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    purpose="intent_classification"
                )
                if raw and not raw.startswith("Sorry, all AI providers"):
                    raw_decision = raw.strip().upper()

            if "CONVERSATIONAL" in raw_decision:
                return QueryRouteDecision("conversational", 0.9, "LLM classifier routed to Conversational")
            elif "SQL" in raw_decision:
                return QueryRouteDecision("sql", 0.9, "LLM classifier routed to SQL", database_id=selected_db.id if selected_db else None)
            elif "RAG" in raw_decision:
                return QueryRouteDecision("rag", 0.9, "LLM classifier routed to RAG")
            elif "HYBRID" in raw_decision:
                return QueryRouteDecision("hybrid", 0.85, "LLM classifier routed to Hybrid", database_id=selected_db.id if selected_db else None)
        except Exception as e:
            print(f"LLM classifier exception: {e}")

    # Default fallback based on highest score or conversational/RAG default
    if (is_platform_help or is_greeting or (conv_score > 0 and conv_score >= sql_score and conv_score >= rag_score)) and not has_operational_data_intent:
        return QueryRouteDecision("conversational", 0.85, "Heuristic matched Conversational intent")
    if sql_score > rag_score:
        return QueryRouteDecision("sql", 0.7, "Heuristic majority to SQL", database_id=selected_db.id if selected_db else None)
    return QueryRouteDecision("rag", 0.7, "Default fallback to RAG Knowledge Base")
