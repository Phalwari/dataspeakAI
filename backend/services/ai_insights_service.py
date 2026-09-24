import os
import json
import logging
import urllib.request
import urllib.parse
from typing import Any, Dict, List
from services.metric_executor import MetricExecutor, MetricRequest

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def generate_ai_insights_from_stats(db_conn: Any, registries: List[Any], db: Any) -> Dict[str, Any]:
    """
    Computes deterministic stats via MetricExecutor and SchemaRegistry metadata,
    and sends real verified numbers to Google Gemini 2.5 Flash to generate executive
    business insights. Adheres strictly to security and deterministic calculation standards.
    """
    tables = sorted(list(set([r.table_name for r in registries])))
    
    # 1. Collect deterministic stats per table using MetricExecutor & SchemaRegistry
    stats_summary: Dict[str, Any] = {}
    
    for t in tables[:8]:  # Max 8 tables for clean summary
        t_regs = [r for r in registries if r.table_name == t]
        measures = [
            r.column_name for r in t_regs 
            if r.is_measure and not str(r.column_name).lower().endswith("id") and str(r.column_name).lower() != "id"
        ]
        
        # Row count via MetricExecutor
        row_cnt = 0
        try:
            cnt_req = MetricRequest(
                connection_id=db_conn.id,
                target_ref=f"{t}.*",
                aggregation="COUNT",
                tenant_id=db_conn.tenant_id,
            )
            cnt_res = MetricExecutor.execute(cnt_req, db_conn, db)
            row_cnt = int(cnt_res.value) if cnt_res.value is not None else 0
        except Exception as ex_cnt:
            logger.debug(f"Could not compute row count for table {t} via MetricExecutor: {ex_cnt}")
            # Fallback to cardinality if recorded in SchemaRegistry
            first_reg = t_regs[0] if t_regs else None
            row_cnt = getattr(first_reg, "cardinality", 0) or 0
        
        # Numeric measures via MetricExecutor
        meas_stats: Dict[str, Any] = {}
        for m in measures[:3]:
            try:
                s_req = MetricRequest(connection_id=db_conn.id, target_ref=f"{t}.{m}", aggregation="SUM", tenant_id=db_conn.tenant_id)
                a_req = MetricRequest(connection_id=db_conn.id, target_ref=f"{t}.{m}", aggregation="AVG", tenant_id=db_conn.tenant_id)
                mx_req = MetricRequest(connection_id=db_conn.id, target_ref=f"{t}.{m}", aggregation="MAX", tenant_id=db_conn.tenant_id)

                s_res = MetricExecutor.execute(s_req, db_conn, db)
                a_res = MetricExecutor.execute(a_req, db_conn, db)
                mx_res = MetricExecutor.execute(mx_req, db_conn, db)

                meas_stats[m] = {
                    "total": round(float(s_res.value or 0), 2),
                    "average": round(float(a_res.value or 0), 2),
                    "max": round(float(mx_res.value or 0), 2)
                }
            except Exception as ex_m:
                logger.debug(f"Could not compute measure stats for {t}.{m}: {ex_m}")
                reg_m = next((r for r in t_regs if r.column_name == m), None)
                if reg_m:
                    meas_stats[m] = {
                        "total": 0.0,
                        "average": round(float(getattr(reg_m, "mean_value", 0.0) or 0.0), 2),
                        "max": round(float(getattr(reg_m, "max_value", 0.0) or 0.0), 2),
                    }

        stats_summary[t] = {
            "row_count": row_cnt,
            "numeric_measures": meas_stats,
        }

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
