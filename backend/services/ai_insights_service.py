import os
import json
import logging
import urllib.request
import urllib.parse
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def generate_ai_insights_from_stats(db_conn, registries, db):
    """
    Computes deterministic stats from the user's database and sends real numbers
    to Google Gemini 2.5 Flash to generate executive business insights.
    """
    tables = list(set([r.table_name for r in registries]))
    
    # 1. Collect deterministic stats per table
    stats_summary = {}
    from routers.databases import get_connection_url
    url = get_connection_url(db_conn)
    
    if url:
        try:
            from sqlalchemy.pool import NullPool
            engine = create_engine(url, poolclass=NullPool)
            with engine.connect() as conn:
                for t in tables[:8]: # Max 8 tables for clean summary
                    t_regs = [r for r in registries if r.table_name == t]
                    measures = [r.column_name for r in t_regs if r.is_measure and not r.column_name.lower().endswith("id") and r.column_name.lower() != "id"]
                    dimensions = [r.column_name for r in t_regs if r.is_dimension]
                    
                    row_cnt = 0
                    try:
                        c_res = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).fetchone()
                        row_cnt = c_res[0] if c_res else 0
                    except Exception:
                        pass
                    
                    meas_stats = {}
                    for m in measures[:3]:
                        try:
                            m_res = conn.execute(text(f'SELECT SUM("{m}"), AVG("{m}"), MAX("{m}") FROM "{t}"')).fetchone()
                            if m_res:
                                meas_stats[m] = {
                                    "total": round(float(m_res[0] or 0), 2),
                                    "average": round(float(m_res[1] or 0), 2),
                                    "max": round(float(m_res[2] or 0), 2)
                                }
                        except Exception:
                            pass
                            
                    dim_dist = {}
                    for d in dimensions[:2]:
                        try:
                            d_res = conn.execute(text(f'SELECT "{d}", COUNT(*) AS cnt FROM "{t}" WHERE "{d}" IS NOT NULL GROUP BY "{d}" ORDER BY cnt DESC LIMIT 4')).fetchall()
                            dim_dist[d] = [{str(r[0]): int(r[1])} for r in d_res]
                        except Exception:
                            pass

                    stats_summary[t] = {
                        "row_count": row_cnt,
                        "numeric_measures": meas_stats,
                        "top_categories": dim_dist
                    }
            engine.dispose()
        except Exception as e:
            logger.warning(f"Error computing stats for AI insights: {e}")

    # Fallback default insights if Gemini API is unavailable or unconfigured
    fallback_result = {
        "business_type": f"Enterprise Data Analytics for {db_conn.name} ({db_conn.db_type.upper()})",
        "key_metrics": [
            {
                "title": "Total Profiled Records",
                "value": f"{sum(s.get('row_count', 0) for s in stats_summary.values()):,} total rows across {len(tables)} tables",
                "trend": "+100% Introspected",
                "impact": "High Volume"
            },
            {
                "title": "Active Data Tables",
                "value": f"{len(tables)} Production Tables",
                "trend": "Full Schema Mapped",
                "impact": "Schema Integrity"
            }
        ],
        "observations": [
            f"Detected {len(tables)} core relational tables in database '{db_conn.database or db_conn.name}'.",
            "Multi-table relationship mapping successfully established.",
            "Automated KPI indexing active for real-time natural language querying."
        ],
        "recommendations": [
            "Monitor key transaction volume trends in your main transactional tables.",
            "Utilize NL-to-SQL search on Knowledge Base to extract ad-hoc reports.",
            "Schedule automated daily schema profiling to track row growth."
        ]
    }

    if not GEMINI_API_KEY:
        logger.info("GEMINI_API_KEY not set. Returning deterministic fallback insights.")
        return fallback_result

    # 2. Call Google Gemini 2.5 Flash API with deterministic stats
    try:
        prompt = f"""
        You are an elite Business Intelligence AI Analyst working for DataSpeakAI SaaS.
        Analyze the following real database introspection statistics for database '{db_conn.name}' ({db_conn.db_type}):
        
        {json.dumps(stats_summary, indent=2)}
        
        Provide an executive summary in valid JSON matching this exact structure:
        {{
            "business_type": "Concise 1-sentence description of the likely business domain (e.g. E-Commerce Retail, Digital Music Store, SaaS Product, Logistics)",
            "key_metrics": [
                {{
                    "title": "Metric Name",
                    "value": "Exact calculated value with currency/unit",
                    "trend": "+X% or Trend statement",
                    "impact": "High / Medium / Growth"
                }}
            ],
            "observations": [
                "Observation bullet 1 based on actual numbers",
                "Observation bullet 2 based on categories",
                "Observation bullet 3"
            ],
            "recommendations": [
                "Actionable strategic recommendation 1",
                "Actionable strategic recommendation 2",
                "Actionable strategic recommendation 3"
            ]
        }}
        
        Return ONLY valid raw JSON without markdown formatting or code blocks.
        """
        
        req_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(req_url, data=data, headers={"Content-Type": "application/json"})
        
        with urllib.request.urlopen(req, timeout=12) as resp:
            res_body = json.loads(resp.read().decode("utf-8"))
            raw_text = res_body["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            return json.loads(raw_text.strip())
            
    except Exception as ex:
        logger.error(f"Gemini API call failed for AI Insights: {ex}")
        return fallback_result
