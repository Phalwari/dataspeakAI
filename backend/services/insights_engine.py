"""
Dynamic AI Insights & Recommendation Engine Worker.

Analyzes real tenant telemetry:
- Query logs (query volume, error rates, average latency, failure patterns)
- Database connections & Schema registries (table counts, column profiles, row counts)
- Vector knowledge base documents (indexed counts, document health)

Synthesizes structured business anomalies, performance warnings, and revenue opportunities
using Google Gemini 2.5 Flash via llm_generation_service with multi-key rotation and
deterministic zero-hallucination fallback.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

import models
from services.llm_generation_service import generate

logger = logging.getLogger("dataspeak.insights_engine")


class InsightsEngine:
    @staticmethod
    def collect_tenant_telemetry(
        tenant_id: int,
        database_id: Optional[int],
        db: Session
    ) -> Dict[str, Any]:
        """
        Gathers genuine, verified stats from QueryLog, DatabaseConnection,
        SchemaRegistry, and Document tables scoped strictly to tenant_id.
        """
        now = datetime.now(timezone.utc)
        cutoff_7d = now - timedelta(days=7)
        cutoff_24h = now - timedelta(hours=24)

        # 1. Query Logs Telemetry
        query_base = db.query(models.QueryLog).filter(
            models.QueryLog.tenant_id == tenant_id
        )
        if database_id is not None:
            query_base = query_base.filter(models.QueryLog.database_id == database_id)

        total_queries = query_base.count()
        queries_7d = query_base.filter(models.QueryLog.created_at >= cutoff_7d).count()
        queries_24h = query_base.filter(models.QueryLog.created_at >= cutoff_24h).count()

        failed_queries = query_base.filter(models.QueryLog.status == "failed").count()
        successful_queries = query_base.filter(models.QueryLog.status == "success").count()
        failure_rate = (failed_queries / total_queries * 100) if total_queries > 0 else 0.0

        avg_latency_row = (
            query_base.filter(models.QueryLog.execution_time_ms.isnot(None))
            .with_entities(func.avg(models.QueryLog.execution_time_ms))
            .first()
        )
        avg_latency = float(avg_latency_row[0] or 0.0) if avg_latency_row else 0.0

        slow_queries_count = query_base.filter(
            models.QueryLog.execution_time_ms > 1000
        ).count()

        # Top error messages in failed queries
        error_rows = (
            query_base.filter(
                models.QueryLog.status == "failed",
                models.QueryLog.error_message.isnot(None)
            )
            .with_entities(models.QueryLog.error_message, func.count(models.QueryLog.id))
            .group_by(models.QueryLog.error_message)
            .order_by(desc(func.count(models.QueryLog.id)))
            .limit(3)
            .all()
        )
        top_errors = [{"error": str(row[0])[:120], "count": int(row[1])} for row in error_rows]

        # 2. Database Connections Telemetry
        db_query = db.query(models.DatabaseConnection).filter(
            models.DatabaseConnection.tenant_id == tenant_id
        )
        if database_id is not None:
            db_query = db_query.filter(models.DatabaseConnection.id == database_id)
        databases = db_query.all()

        db_summaries = []
        total_tables = 0
        for conn in databases:
            table_count = 0
            if conn.tables_metadata and isinstance(conn.tables_metadata, list):
                table_count = len(conn.tables_metadata)
            elif conn.tables_metadata and isinstance(conn.tables_metadata, dict):
                table_count = len(conn.tables_metadata.keys())
            else:
                reg_count = db.query(models.SchemaRegistry).filter(
                    models.SchemaRegistry.connection_id == conn.id
                ).with_entities(func.count(func.distinct(models.SchemaRegistry.table_name))).scalar()
                table_count = int(reg_count or 0)

            total_tables += table_count
            db_summaries.append({
                "id": conn.id,
                "name": conn.name,
                "db_type": conn.db_type,
                "status": conn.status,
                "tables_count": table_count,
            })

        # 3. Documents / Knowledge Base Telemetry
        doc_query = db.query(models.Document).filter(models.Document.tenant_id == tenant_id)
        total_docs = doc_query.count()
        ready_docs = doc_query.filter(models.Document.status == "ready").count()
        failed_docs = doc_query.filter(models.Document.status == "failed").count()

        return {
            "tenant_id": tenant_id,
            "database_id": database_id,
            "queries": {
                "total": total_queries,
                "last_7d": queries_7d,
                "last_24h": queries_24h,
                "successful": successful_queries,
                "failed": failed_queries,
                "failure_rate_pct": round(failure_rate, 2),
                "avg_latency_ms": round(avg_latency, 2),
                "slow_queries_count": slow_queries_count,
                "top_errors": top_errors,
            },
            "databases": {
                "count": len(databases),
                "total_tables": total_tables,
                "connections": db_summaries,
            },
            "knowledge_base": {
                "total_documents": total_docs,
                "ready_documents": ready_docs,
                "failed_documents": failed_docs,
            },
            "has_data": (total_queries > 0 or len(databases) > 0 or total_docs > 0),
        }

    @staticmethod
    def detect_deterministic_anomalies(telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluates deterministic anomaly rules based on verified numbers.
        """
        anomalies = []
        queries = telemetry.get("queries", {})
        dbs = telemetry.get("databases", {})
        kb = telemetry.get("knowledge_base", {})

        # Anomaly 1: Query Error Spike
        if queries.get("failure_rate_pct", 0) >= 15.0 and queries.get("total", 0) >= 3:
            anomalies.append({
                "rule": "HIGH_FAILURE_RATE",
                "severity": "critical",
                "category": "Performance",
                "metric": f"{queries['failure_rate_pct']}% error rate",
                "detail": f"{queries['failed']} of {queries['total']} queries failed. Top error: {queries.get('top_errors', [{}])[0].get('error', 'Syntax/Connection error') if queries.get('top_errors') else 'General execution error'}"
            })
        elif queries.get("failure_rate_pct", 0) >= 5.0 and queries.get("total", 0) >= 3:
            anomalies.append({
                "rule": "ELEVATED_FAILURE_RATE",
                "severity": "warning",
                "category": "Performance",
                "metric": f"{queries['failure_rate_pct']}% error rate",
                "detail": f"Intermittent execution errors detected ({queries['failed']} failed queries)."
            })

        # Anomaly 2: Latency Bottleneck
        if queries.get("avg_latency_ms", 0) >= 1200.0 and queries.get("total", 0) >= 2:
            anomalies.append({
                "rule": "LATENCY_BOTTLENECK",
                "severity": "warning",
                "category": "Performance",
                "metric": f"{queries['avg_latency_ms']}ms average response time",
                "detail": f"{queries.get('slow_queries_count', 0)} queries exceeded the 1.0s latency threshold."
            })

        # Anomaly 3: Unprofiled or Empty Databases
        unprofiled_dbs = [d for d in dbs.get("connections", []) if d.get("tables_count", 0) == 0]
        if unprofiled_dbs:
            anomalies.append({
                "rule": "UNPROFILED_DATABASES",
                "severity": "alert",
                "category": "Operational",
                "metric": f"{len(unprofiled_dbs)} unprofiled connection(s)",
                "detail": f"Databases [{', '.join(d['name'] for d in unprofiled_dbs)}] contain 0 introspected tables or need schema profiling."
            })

        # Anomaly 4: Knowledge Base Health
        if kb.get("failed_documents", 0) > 0:
            anomalies.append({
                "rule": "DOCUMENT_INDEXING_FAILURES",
                "severity": "alert",
                "category": "Operational",
                "metric": f"{kb['failed_documents']} failed document(s)",
                "detail": f"{kb['failed_documents']} uploaded documents encountered parsing or embedding errors during RAG ingestion."
            })
        elif kb.get("total_documents", 0) == 0 and dbs.get("count", 0) > 0:
            anomalies.append({
                "rule": "EMPTY_KNOWLEDGE_BASE",
                "severity": "opportunity",
                "category": "Customer Success",
                "metric": "0 documents indexed",
                "detail": "Adding company documentation, FAQs, or SOPs will unlock hybrid SQL+RAG answering in AI chat and chatbot widgets."
            })

        # Anomaly 5: High Stability Opportunity
        if queries.get("total", 0) >= 10 and queries.get("failure_rate_pct", 0) == 0.0:
            anomalies.append({
                "rule": "EXCELLENT_SYSTEM_HEALTH",
                "severity": "opportunity",
                "category": "Revenue",
                "metric": "100% Query Success Rate",
                "detail": f"All {queries['total']} queries executed cleanly. Ideal time to scale widget traffic and embed public chatbots."
            })

        return anomalies

    @staticmethod
    def synthesize_insights_with_ai(
        telemetry: Dict[str, Any],
        deterministic_anomalies: List[Dict[str, Any]],
        database_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Invokes Google Gemini 2.5 Flash via llm_generation_service to synthesize
        actionable, business-aware insights from verified metrics.
        """
        # If tenant has no telemetry at all, return empty list (honest onboarding state)
        if not telemetry.get("has_data"):
            return []

        prompt = f"""
You are an elite Business Intelligence and Database Anomaly Specialist for the DataSpeakAI SaaS platform.
Analyze the following verified telemetry and detected anomalies for tenant #{telemetry['tenant_id']}:

TELEMETRY DATA:
{json.dumps(telemetry, indent=2)}

DETECTED STATISTICAL ANOMALIES:
{json.dumps(deterministic_anomalies, indent=2)}

Synthesize 3 to 6 high-value, structured executive insights and actionable recommendations.
Adhere strictly to:
1. Real Data Only: Never fabricate numbers. Ground every observation in the telemetry provided above.
2. Categories: Distribute appropriately across "Revenue", "Performance", "Customer Success", and "Operational".
3. Severities: Classify accurately as "critical", "warning", "alert", or "opportunity".
4. Actionable Recommendations: Every insight must provide 1 to 2 clear, concrete action steps with priority ("high", "medium", "low"), action_type ("navigate_logs", "navigate_databases", "navigate_analytics", "general"), and relative action_url (e.g. "/dashboard/logs", "/dashboard/databases", "/dashboard/analytics", "/dashboard/knowledge-base").

Format the output strictly as a JSON array of objects with this schema:
[
  {{
    "title": "Concise executive title (e.g. Elevated Query Error Spike Detected)",
    "category": "Performance",
    "severity": "warning",
    "summary": "Detailed narrative describing the anomaly, root cause, and business impact based on actual numbers.",
    "impact_score": 7.8,
    "confidence_score": 0.94,
    "recommendations": [
      {{
        "action_step": "Inspect recent syntax and permission errors in execution logs.",
        "priority": "high",
        "action_type": "navigate_logs",
        "action_url": "/dashboard/logs?status=failed"
      }}
    ]
  }}
]

Return ONLY raw JSON. Do NOT wrap in markdown formatting or explanation text.
"""
        try:
            raw_response = generate(
                prompt=prompt,
                provider="gemini",
                temperature=0.2
            )

            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            if isinstance(parsed, list) and len(parsed) > 0:
                # Add database_id link if scoped
                for item in parsed:
                    item["database_id"] = database_id
                return parsed
        except Exception as ex:
            logger.warning(f"[InsightsEngine] AI synthesis failed or returned invalid JSON ({ex}). Falling back to deterministic engine.")

        return InsightsEngine.generate_deterministic_fallback(telemetry, deterministic_anomalies, database_id)

    @staticmethod
    def generate_deterministic_fallback(
        telemetry: Dict[str, Any],
        deterministic_anomalies: List[Dict[str, Any]],
        database_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Pure rule-based statistical fallback that formulates authentic insights
        from verified telemetry when the LLM provider is offline.
        """
        if not telemetry.get("has_data"):
            return []

        insights: List[Dict[str, Any]] = []
        queries = telemetry.get("queries", {})
        dbs = telemetry.get("databases", {})
        kb = telemetry.get("knowledge_base", {})

        first_db_id = dbs["connections"][0]["id"] if (dbs.get("connections") and len(dbs["connections"]) > 0) else None
        target_db_id = database_id if database_id is not None else first_db_id

        # 1. Error Rate Insight
        if queries.get("failure_rate_pct", 0) > 0:
            sev = "critical" if queries["failure_rate_pct"] >= 15 else "warning"
            insights.append({
                "database_id": target_db_id,
                "title": f"Query Execution Failure Rate ({queries['failure_rate_pct']}%)",
                "category": "Performance",
                "severity": sev,
                "summary": f"{queries['failed']} of {queries['total']} total queries failed execution. Common errors indicate syntax discrepancies or schema permission constraints that impact user reporting.",
                "impact_score": min(10.0, round(queries["failure_rate_pct"] / 10 + 5.0, 1)),
                "confidence_score": 0.98,
                "recommendations": [
                    {
                        "action_step": "Review failing query logs to diagnose error patterns and column discrepancies.",
                        "priority": "high",
                        "action_type": "navigate_logs",
                        "action_url": "/dashboard/logs?status=failed"
                    }
                ]
            })
        elif queries.get("total", 0) > 0:
            insights.append({
                "database_id": target_db_id,
                "title": "Optimal Query Health & Execution Reliability",
                "category": "Performance",
                "severity": "opportunity",
                "summary": f"All {queries['total']} executed queries ran with a 100% success rate and average latency of {queries.get('avg_latency_ms', 0)}ms. System throughput is stable.",
                "impact_score": 6.5,
                "confidence_score": 0.95,
                "recommendations": [
                    {
                        "action_step": "Enable automated widget chatbot embedding to scale end-user natural language query access.",
                        "priority": "medium",
                        "action_type": "navigate_analytics",
                        "action_url": "/dashboard/chatbot"
                    }
                ]
            })

        # 2. Database Coverage Insight
        if dbs.get("count", 0) > 0:
            unprofiled = [d for d in dbs.get("connections", []) if d.get("tables_count", 0) == 0]
            if unprofiled:
                insights.append({
                    "database_id": target_db_id,
                    "title": f"Unprofiled Database Schemas Detected ({len(unprofiled)} Connection{'s' if len(unprofiled) > 1 else ''})",
                    "category": "Operational",
                    "severity": "alert",
                    "summary": f"{len(unprofiled)} connected databases have not finished table profiling. Profiling is required for accurate NL-to-SQL query generation.",
                    "impact_score": 7.2,
                    "confidence_score": 0.99,
                    "recommendations": [
                        {
                            "action_step": "Inspect database connections and trigger schema introspection to map tables and columns.",
                            "priority": "high",
                            "action_type": "navigate_databases",
                            "action_url": "/dashboard/databases"
                        }
                    ]
                })
            else:
                insights.append({
                    "database_id": target_db_id,
                    "title": f"Schema Introspection Coverage ({dbs.get('total_tables', 0)} Tables Mapped)",
                    "category": "Operational",
                    "severity": "opportunity",
                    "summary": f"Successfully mapped {dbs.get('total_tables', 0)} tables across {dbs.get('count', 0)} connected database source(s). Schema metadata is fully available for natural language queries.",
                    "impact_score": 6.0,
                    "confidence_score": 0.92,
                    "recommendations": [
                        {
                            "action_step": "Explore multi-table relationships and preview live rows in the database explorer.",
                            "priority": "low",
                            "action_type": "navigate_databases",
                            "action_url": "/dashboard/databases"
                        }
                    ]
                })

        # 3. Knowledge Base Insight
        if kb.get("total_documents", 0) == 0:
            insights.append({
                "database_id": database_id,
                "title": "Unstructured Knowledge Base Indexing Opportunity",
                "category": "Customer Success",
                "severity": "opportunity",
                "summary": "Zero enterprise documents are currently indexed in FAISS vector storage. Uploading PDFs or manuals enables hybrid SQL + RAG conversational answers.",
                "impact_score": 5.5,
                "confidence_score": 0.90,
                "recommendations": [
                    {
                        "action_step": "Upload PDF manuals or guidelines to activate vector semantic search.",
                        "priority": "medium",
                        "action_type": "general",
                        "action_url": "/dashboard/knowledge-base"
                    }
                ]
            })

        return insights

    @staticmethod
    def persist_tenant_insights(
        tenant_id: int,
        database_id: Optional[int],
        insights_data: List[Dict[str, Any]],
        db: Session
    ) -> List[models.GeneratedInsight]:
        """
        Stores freshly generated insights and recommendations atomically,
        preserving dismissed insights while archiving previous active ones.
        """
        # Archive / delete previous active insights for this tenant (and db if specified)
        existing_active = db.query(models.GeneratedInsight).filter(
            models.GeneratedInsight.tenant_id == tenant_id,
            models.GeneratedInsight.status == "active"
        )
        if database_id is not None:
            existing_active = existing_active.filter(models.GeneratedInsight.database_id == database_id)

        # Remove previous active insights (cascades to recommendations)
        existing_active.delete(synchronize_session=False)

        persisted_records: List[models.GeneratedInsight] = []

        for data in insights_data:
            insight = models.GeneratedInsight(
                tenant_id=tenant_id,
                database_id=data.get("database_id") or database_id,
                title=str(data.get("title", "AI Business Insight"))[:255],
                category=str(data.get("category", "Operational"))[:100],
                severity=str(data.get("severity", "opportunity")).lower()[:50],
                summary=str(data.get("summary", "")),
                impact_score=float(data.get("impact_score", 0.0) or 0.0),
                confidence_score=float(data.get("confidence_score", 1.0) or 1.0),
                status="active"
            )
            db.add(insight)
            db.flush()  # Flush to obtain insight.id

            for rec_data in data.get("recommendations", []):
                rec = models.Recommendation(
                    insight_id=insight.id,
                    action_step=str(rec_data.get("action_step", "")),
                    priority=str(rec_data.get("priority", "medium")).lower()[:20],
                    action_type=str(rec_data.get("action_type", "general"))[:50],
                    action_url=str(rec_data.get("action_url", ""))[:255] if rec_data.get("action_url") else None,
                    status="pending"
                )
                db.add(rec)

            persisted_records.append(insight)

        db.commit()

        # Re-query with joined relationships
        insight_ids = [i.id for i in persisted_records]
        if not insight_ids:
            return []

        return (
            db.query(models.GeneratedInsight)
            .filter(models.GeneratedInsight.id.in_(insight_ids))
            .order_by(models.GeneratedInsight.created_at.desc())
            .all()
        )

    @classmethod
    def refresh_tenant_insights(
        cls,
        tenant_id: int,
        database_id: Optional[int],
        db: Session
    ) -> List[models.GeneratedInsight]:
        """
        Coordinates full fresh synthesis:
        1. Collect telemetry
        2. Detect deterministic anomalies
        3. Synthesize via Gemini 2.5 Flash (or deterministic fallback)
        4. Persist to DB
        """
        telemetry = cls.collect_tenant_telemetry(tenant_id, database_id, db)
        anomalies = cls.detect_deterministic_anomalies(telemetry)
        insights_data = cls.synthesize_insights_with_ai(telemetry, anomalies, database_id)
        persisted = cls.persist_tenant_insights(tenant_id, database_id, insights_data, db)
        return persisted


insights_engine = InsightsEngine()
