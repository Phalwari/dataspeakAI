"""
chart_layout_agent.py
----------------------
Agent 3: Semantic Analysis + chosen KPIs dekh kar har KPI ke liye best
chart-type, axis-labels, legend, aur filters decide karta hai — jaise
ek human BI designer PowerBI me manually karta.
"""

import os
import json
import logging
from typing import cast
from langchain_google_genai import ChatGoogleGenerativeAI

from .schemas import SemanticAnalysis, KpiAgentOutput, ChartLayoutOutput
from .prompts import CHART_LAYOUT_AGENT_PROMPT

logger = logging.getLogger("nexabi.agents.chart_layout")

AGENT_TIMEOUT_SECONDS = 20


async def run_chart_layout_agent(
    semantic: SemanticAnalysis, kpi_output: KpiAgentOutput, llm_model: str = "gemini-3.6-flash"
) -> ChartLayoutOutput:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    kwargs = {"google_api_key": api_key} if api_key else {}

    llm = ChatGoogleGenerativeAI(model=llm_model, temperature=0.2, timeout=AGENT_TIMEOUT_SECONDS, **kwargs)
    structured_llm = llm.with_structured_output(ChartLayoutOutput)

    prompt = CHART_LAYOUT_AGENT_PROMPT.format(
        business_domain=semantic.business_domain,
        semantic_json=json.dumps([c.model_dump() for c in semantic.columns], indent=2),
        kpis_json=json.dumps([k.model_dump() for k in kpi_output.kpis], indent=2),
    )

    try:
        result = cast(ChartLayoutOutput, await structured_llm.ainvoke(prompt))
        logger.info("Chart/Layout agent: %d charts, %d filters", len(result.charts), len(result.filters))
        return result
    except Exception as e:
        logger.error("Chart/Layout agent failed: %s", e, exc_info=True)
        raise
