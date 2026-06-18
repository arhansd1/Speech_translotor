# agent/state.py
# Defines the AgentState TypedDict that flows through every LangGraph node.
# LangGraph passes this state from node to node; each node reads what it needs
# and writes back only the fields it modifies.

from typing import Optional, TypedDict, Annotated
import operator


class AgentState(TypedDict):
    # ── Inputs (set before the graph runs) ──────────────────────────────────
    raw_translation: str          # Translation from Sarvam STT+Translate endpoint
    source_language: str          # BCP-47 detected source language (e.g. "hi-IN")
    target_language: str          # BCP-47 target language chosen by user (e.g. "ta-IN")
    transcript: str               # Original transcript in source language
    session_context: str          # Working memory context string (last 5 turns)
    api_key: str                  # Sarvam API key for this request (demo or BYOK)

    # ── Agent working state ──────────────────────────────────────────────────
    quality_issues: list[str]     # List of detected quality problems (empty = clean)
    glossary_terms: list[str]     # Technical terms found that need glossary lookup
    glossary_results: list[dict]  # Results from glossary MCP tool

    # ── Output ───────────────────────────────────────────────────────────────
    final_translation: str        # Polished translation the TTS will speak
    agent_reasoning: str          # What the agent did (for LangSmith + debug panel)
    error: Optional[str]          # Set if any node fails; triggers error path
