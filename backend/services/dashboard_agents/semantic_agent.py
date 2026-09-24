"""
semantic_agent.py
-----------------
Agent 1: Schema dekh kar business-domain aur har column ka REAL
business-meaning nikalta hai. Raw rows kabhi nahi bhejte — sirf
schema + lightweight stats (jo profiler.py se aati hain).
"""

import os
import json
import logging
from typing import cast
from langchain_google_genai import ChatGoogleGenerativeAI

from .schemas import SemanticAnalysis
from .prompts import SEMANTIC_AGENT_PROMPT

logger = logging.getLogger("nexabi.agents.semantic")

AGENT_TIMEOUT_SECONDS = 20


def _schema_to_llm_input(table_profile) -> dict:
    """
    profiler.py ke TableProfile object ko LLM-friendly JSON me convert karo.
    RAW ROWS kabhi include mat karo — sirf metadata + top-10 sample values.
    """
    return {
        "table_name": table_profile.table_name,
        "row_count": table_profile.row_count,
        "columns": [
            {
                "name": c.name,
                "data_type": c.data_type,
                "cardinality": c.cardinality,
                "null_percentage": c.null_percentage,
                "min_value": c.min_value,
                "max_value": c.max_value,
                "sample_top_values": c.top_values[:10] if getattr(c, "top_values", None) else None,
            }
            for c in table_profile.columns
        ],
    }


async def run_semantic_agent(table_profiles: list, llm_model: str = "gemini-3.6-flash") -> SemanticAnalysis:
    schema_payload = [_schema_to_llm_input(tp) for tp in table_profiles]
    schema_json = json.dumps(schema_payload, indent=2, default=str)

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    kwargs = {"google_api_key": api_key} if api_key else {}

    llm = ChatGoogleGenerativeAI(model=llm_model, temperature=0.1, timeout=AGENT_TIMEOUT_SECONDS, **kwargs)
    structured_llm = llm.with_structured_output(SemanticAnalysis)

    prompt = SEMANTIC_AGENT_PROMPT.format(schema_json=schema_json)

    try:
        result = cast(SemanticAnalysis, await structured_llm.ainvoke(prompt))
        logger.info("Semantic agent: domain=%s confidence=%.2f columns=%d",
                     result.business_domain, result.domain_confidence, len(result.columns))
        return result
    except Exception as e:
        logger.error("Semantic agent failed: %s", e, exc_info=True)
        raise
