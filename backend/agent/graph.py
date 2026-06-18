# agent/graph.py
# Assembles the LangGraph StateGraph.
# Import and call build_graph() once at startup; the compiled graph is reused
# for every translation request (compiling is expensive, running is cheap).
#
# Flow:
#   START
#     → check_quality          (always runs — fast heuristics)
#         ↓ (conditional)
#         ├─ "passthrough"      (clean translation → accept as-is)
#         ├─ "glossary_lookup"  (has domain terms → look up then refine)
#         └─ "refine_translation" (quality issues, no glossary → LLM directly)
#     → END

import logging
from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    check_quality,
    run_glossary_lookup,
    refine_translation,
    passthrough,
    route_after_quality_check,
    route_after_glossary,
)

logger = logging.getLogger(__name__)


def build_graph():
    """
    Builds and compiles the LangGraph graph.
    Returns a compiled graph ready to invoke with .ainvoke(state).
    """
    graph = StateGraph(AgentState)

    # ── Register nodes ──────────────────────────────────────────────────────
    # Node names must match the return values of router functions
    graph.add_node("check_quality", check_quality)
    graph.add_node("glossary_lookup", run_glossary_lookup)
    graph.add_node("refine_translation", refine_translation)
    graph.add_node("passthrough", passthrough)

    # ── Entry point ──────────────────────────────────────────────────────────
    graph.set_entry_point("check_quality")

    # ── Conditional edges from quality check ─────────────────────────────────
    # route_after_quality_check returns one of three node names
    graph.add_conditional_edges(
        "check_quality",
        route_after_quality_check,
        {
            "glossary_lookup": "glossary_lookup",
            "refine_translation": "refine_translation",
            "passthrough": "passthrough",
        },
    )

    # ── After glossary lookup → always refine ────────────────────────────────
    graph.add_edge("glossary_lookup", "refine_translation")

    # ── Terminal nodes → END ─────────────────────────────────────────────────
    graph.add_edge("refine_translation", END)
    graph.add_edge("passthrough", END)

    compiled = graph.compile()
    logger.info("LangGraph agent compiled successfully")
    return compiled


# Module-level compiled graph — built once, reused per request
# Lazy initialization: only built when first imported (avoids startup errors
# if LangGraph isn't installed yet during development)
_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_agent(
    raw_translation: str,
    transcript: str,
    source_language: str,
    target_language: str,
    session_context: str,
    api_key: str,
) -> dict:
    """
    Public interface for main.py.
    Runs the full agent graph and returns the result.
    Always returns a dict with 'final_translation' and 'agent_reasoning'.
    Never raises — errors are captured in the state and logged.
    """
    initial_state: AgentState = {
        "raw_translation": raw_translation,
        "transcript": transcript,
        "source_language": source_language,
        "target_language": target_language,
        "session_context": session_context,
        "api_key": api_key,
        # Working fields — agent fills these in
        "quality_issues": [],
        "glossary_terms": [],
        "glossary_results": [],
        "final_translation": "",
        "agent_reasoning": "",
        "error": None,
    }

    try:
        graph = get_graph()
        result_state = await graph.ainvoke(initial_state)
        return {
            "final_translation": result_state.get("final_translation", raw_translation),
            "agent_reasoning": result_state.get("agent_reasoning", ""),
            "quality_issues": result_state.get("quality_issues", []),
            "glossary_used": len(result_state.get("glossary_results", [])) > 0,
        }
    except Exception as e:
        logger.error(f"Agent graph failed: {e}", exc_info=True)
        # Graceful degradation: return raw translation so user isn't blocked
        return {
            "final_translation": raw_translation,
            "agent_reasoning": f"Agent error (degraded to raw): {e}",
            "quality_issues": [],
            "glossary_used": False,
        }
