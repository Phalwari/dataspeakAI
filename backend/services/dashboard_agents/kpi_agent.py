"""
kpi_agent.py
------------
Agent 2: Semantic Analysis (Agent 1 ka output) lekar business ke liye
sabse meaningful 4-6 KPIs choose karta hai — sirf numeric-sum nahi,
balke computed metrics (profit margin, conversion rate) bhi consider karta hai.
"""

import os
import json
import logging
from typing import cast
from langchain_google_genai import ChatGoogleGenerativeAI

from .schemas import SemanticAnalysis, KpiAgentOutput
from .prompts import KPI_AGENT_PROMPT

logger = logging.getLogger("nexabi.agents.kpi")

AGENT_TIMEOUT_SECONDS = 20


async def run_kpi_agent(semantic: SemanticAnalysis, llm_model: str = "gemini-3.6-flash") -> KpiAgentOutput:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    kwargs = {"google_api_key": api_key} if api_key else {}

    llm = ChatGoogleGenerativeAI(model=llm_model, temperature=0.2, timeout=AGENT_TIMEOUT_SECONDS, **kwargs)
    structured_llm = llm.with_structured_output(KpiAgentOutput)

    prompt = KPI_AGENT_PROMPT.format(
        business_domain=semantic.business_domain,
        semantic_json=json.dumps([c.model_dump() for c in semantic.columns], indent=2),
    )

    try:
        result = cast(KpiAgentOutput, await structured_llm.ainvoke(prompt))
        logger.info("KPI agent: %d KPIs generated", len(result.kpis))
        return result
    except Exception as e:
        logger.error("KPI agent failed: %s", e, exc_info=True)
        raise
