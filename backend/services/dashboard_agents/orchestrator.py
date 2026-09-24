"""
orchestrator.py
----------------
LangGraph state-graph jo 4 agents ko sequence me chalata hai:
semantic_agent → kpi_agent → chart_layout_agent → validator

Poora pipeline ek background job ke andar ek dafa chalta hai (profiling
ke waqt) — dashboard-view time pe kabhi nahi. Result permanently
kpi_definitions/dashboard_layouts table me save hota hai.

Agar kahin bhi LLM call fail ho (timeout, API error), poori pipeline
turant rule-based fallback pe switch ho jati hai — dashboard kabhi
khaali nahi jata.
"""

import asyncio
import logging
from typing import Optional, List, Any, cast
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END

from .schemas import SemanticAnalysis, KpiAgentOutput, ChartLayoutOutput, ValidatedDashboardConfig
from .semantic_agent import run_semantic_agent
from .kpi_agent import run_kpi_agent
from .chart_layout_agent import run_chart_layout_agent
from .validator import validate_dashboard_config
from .fallback_rule_engine import generate_fallback_config

logger = logging.getLogger("nexabi.agents.orchestrator")

PIPELINE_TOTAL_TIMEOUT_SECONDS = 120   # poori pipeline ke liye overall safety cap


class PipelineState(TypedDict, total=False):
    table_profiles: List[Any]           # profiler.TableProfile list
    semantic: Optional[SemanticAnalysis]
    kpi_output: Optional[KpiAgentOutput]
    chart_output: Optional[ChartLayoutOutput]
    final_config: Optional[ValidatedDashboardConfig]
    error: Optional[str]


# ---------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------

async def node_semantic(state: PipelineState) -> PipelineState:
    semantic = await run_semantic_agent(state.get("table_profiles", []))
    return {"semantic": semantic}


async def node_kpi(state: PipelineState) -> PipelineState:
    semantic = state.get("semantic")
    if not semantic:
        raise ValueError("Semantic analysis is missing")
    kpi_output = await run_kpi_agent(semantic)
    return {"kpi_output": kpi_output}


async def node_chart_layout(state: PipelineState) -> PipelineState:
    semantic = state.get("semantic")
    kpi_output = state.get("kpi_output")
    if not semantic or not kpi_output:
        raise ValueError("Semantic analysis or KPI output is missing")
    chart_output = await run_chart_layout_agent(semantic, kpi_output)
    return {"chart_output": chart_output}


async def node_validate(state: PipelineState) -> PipelineState:
    semantic = state.get("semantic")
    kpi_output = state.get("kpi_output")
    chart_output = state.get("chart_output")
    table_profiles = state.get("table_profiles", [])

    if not semantic or not kpi_output or not chart_output:
        final_config = generate_fallback_config(table_profiles)
    else:
        final_config = validate_dashboard_config(
            semantic, kpi_output, chart_output, table_profiles
        )
    # Agar validator ne saari KPIs drop kar di (worst-case hallucination), fallback pe jao
    if not final_config.kpis:
        logger.warning("All KPIs failed validation — switching to fallback")
        final_config = generate_fallback_config(table_profiles)
    return {"final_config": final_config}


def build_graph():
    graph = StateGraph(PipelineState)  # type: ignore[arg-type]
    graph.add_node("semantic", node_semantic)
    graph.add_node("kpi", node_kpi)
    graph.add_node("chart_layout", node_chart_layout)
    graph.add_node("validate", node_validate)

    graph.set_entry_point("semantic")
    graph.add_edge("semantic", "kpi")
    graph.add_edge("kpi", "chart_layout")
    graph.add_edge("chart_layout", "validate")
    graph.add_edge("validate", END)

    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


# ---------------------------------------------------------------------
# Public entrypoint — ISI function ko background job call karega
# ---------------------------------------------------------------------

async def generate_dashboard_via_agents(table_profiles: list) -> ValidatedDashboardConfig:
    """
    Main entrypoint. Background profiling-job se call hoga, ek hi baar.
    Guaranteed: kabhi exception raise nahi karega — fail hone pe fallback
    config return karega, taake calling code (background job) hamesha
    kuch na kuch valid config DB me save kar sake.
    """
    graph = get_compiled_graph()

    try:
        result_state = await asyncio.wait_for(
            graph.ainvoke({"table_profiles": table_profiles}),
            timeout=PIPELINE_TOTAL_TIMEOUT_SECONDS,
        )
        config = result_state.get("final_config")
        if config is None:
            raise RuntimeError("Pipeline completed but produced no final_config")
        return config

    except asyncio.TimeoutError:
        logger.error("Multi-agent pipeline timed out after %ds — using fallback", PIPELINE_TOTAL_TIMEOUT_SECONDS)
        return generate_fallback_config(table_profiles)

    except Exception as e:
        logger.error("Multi-agent pipeline failed: %s — using fallback", e, exc_info=True)
        return generate_fallback_config(table_profiles)
