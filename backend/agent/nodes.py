# agent/nodes.py
# Each function here is a LangGraph node — it receives AgentState, does one job,
# and returns a dict of fields to update in the state.
# Nodes never mutate state directly; they return partial updates.

import os
import re
import logging
import httpx
from typing import Any

from .state import AgentState
from mcp.glossary_lookup import lookup_term
from sarvam.client import SarvamClient, SarvamError

logger = logging.getLogger(__name__)

SARVAM_LLM_BASE = "https://api.sarvam.ai"
SARVAM_LLM_MODEL = "sarvam-105b"   # "sarvam-m" is legacy/deprecated and not in the current allowed model list


# ─────────────────────────────────────────────
# Node 1: Quality Check
# Decides if the raw translation needs any improvement.
# Simple heuristics first, LLM fallback for edge cases.
# ─────────────────────────────────────────────

def check_quality(state: AgentState) -> dict:
    """
    Scans the raw translation for common quality issues:
    - Partial/empty translation
    - [UNTRANSLATED] markers (Sarvam sometimes returns these for unknown words)
    - Suspicious English words that should have been translated
    - Very short output relative to input (truncation indicator)
    Returns quality_issues list and glossary_terms list.
    """
    translation = state["raw_translation"]
    issues = []
    glossary_terms = []

    # Issue 1: Empty or whitespace-only translation
    if not translation.strip():
        issues.append("empty_translation")

    # Issue 2: [UNTRANSLATED] markers left by Sarvam
    if "[UNTRANSLATED]" in translation:
        issues.append("has_untranslated_markers")

    # Issue 3: Suspicious domain terms that may need glossary verification
    # Check against our glossary keys — if a known technical term appears in
    # the transcript (source), verify the translation handles it correctly
    transcript = state.get("transcript", "")
    for term in ["hypertension", "diabetes", "affidavit", "injunction",
                 "algorithm", "machine learning", "mutual fund"]:
        if term.lower() in transcript.lower():
            glossary_terms.append(term)

    # Issue 4: Very short translation vs source (possible truncation)
    source_words = len(state.get("transcript", "").split())
    trans_words = len(translation.split())
    if source_words > 5 and trans_words < source_words * 0.3:
        issues.append("possible_truncation")

    reasoning = f"Quality check: {len(issues)} issues found"
    if glossary_terms:
        reasoning += f", {len(glossary_terms)} glossary terms to verify"

    return {
        "quality_issues": issues,
        "glossary_terms": glossary_terms,
        "agent_reasoning": reasoning,
    }


# ─────────────────────────────────────────────
# Node 2: Glossary Lookup
# Called only when quality check finds domain terms.
# ─────────────────────────────────────────────

def run_glossary_lookup(state: AgentState) -> dict:
    """
    Looks up each identified glossary term.
    Uses the in-memory dict (Qdrant later — same interface).
    """
    terms = state.get("glossary_terms", [])
    target_lang = state["target_language"]
    results = []

    for term in terms:
        result = lookup_term(term, target_language_code=target_lang)
        if result["found"]:
            results.append(result)
            logger.info(f"Glossary hit: {term} → {result.get('preferred_translation', 'no hint')}")

    return {
        "glossary_results": results,
        "agent_reasoning": state["agent_reasoning"] + f" | Glossary: {len(results)} hits",
    }


# ─────────────────────────────────────────────
# Node 3: Refine Translation (LLM call)
# Only called when there are quality issues or glossary terms to apply.
# Uses Sarvam 105B as the LLM brain.
# ─────────────────────────────────────────────

async def refine_translation(state: AgentState) -> dict:
    """
    Calls Sarvam 105B to polish the translation, injecting:
    - The raw translation
    - Quality issues found
    - Glossary term hints
    - Working memory context (recent turns)
    Returns final_translation.
    """
    issues = state.get("quality_issues", [])
    glossary_results = state.get("glossary_results", [])
    context = state.get("session_context", "")

    # Build the refinement prompt
    glossary_context = ""
    if glossary_results:
        hints = []
        for g in glossary_results:
            if "preferred_translation" in g:
                hints.append(f"- '{g['term']}' should be translated as '{g['preferred_translation']}'")
        if hints:
            glossary_context = "\n\nGlossary hints to apply:\n" + "\n".join(hints)

    issues_context = ""
    if issues:
        issues_context = f"\n\nKnown issues to fix: {', '.join(issues)}"

    system_prompt = (
        f"You are a professional translator specializing in Indian languages. "
        f"Your task is to refine a translation from {state['source_language']} "
        f"to {state['target_language']}. "
        f"Return ONLY the improved translation text, nothing else."
    )

    user_prompt = (
        f"Original text: {state['transcript']}\n\n"
        f"Current translation (needs improvement): {state['raw_translation']}"
        f"{issues_context}"
        f"{glossary_context}"
        f"\n\n{context}"
        f"\n\nProvide an improved, natural translation:"
    )

    try:
        api_key = state["api_key"]
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{SARVAM_LLM_BASE}/v1/chat/completions",
                headers={"api-subscription-key": api_key},
                json={
                    "model": SARVAM_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.3,  # Low temp for translation (more deterministic)
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # refined = data["choices"][0]["message"]["content"].strip()
            # FIX: Safely access nested dictionary keys and handle None
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            refined = (content or "").strip()


        return {
            "final_translation": refined,
            "agent_reasoning": state["agent_reasoning"] + " | LLM refined translation",
        }

    except Exception as e:
        # If LLM refinement fails, fall back to raw translation — never block the user
        logger.warning(f"LLM refinement failed, using raw translation: {e}")
        return {
            "final_translation": state["raw_translation"],
            "agent_reasoning": state["agent_reasoning"] + f" | LLM failed ({e}), used raw",
            "error": None,  # Not a fatal error — degraded gracefully
        }


# ─────────────────────────────────────────────
# Node 4: Pass Through
# Used when translation is clean — no processing needed
# ─────────────────────────────────────────────

def passthrough(state: AgentState) -> dict:
    """Translation is clean. Accept it as-is."""
    return {
        "final_translation": state["raw_translation"],
        "agent_reasoning": state["agent_reasoning"] + " | Translation accepted as-is",
    }


# ─────────────────────────────────────────────
# Router: decides which path to take after quality check
# ─────────────────────────────────────────────

def route_after_quality_check(state: AgentState) -> str:
    """
    Returns the name of the next node to run.
    LangGraph uses this as the conditional edge function.
    """
    issues = state.get("quality_issues", [])
    glossary_terms = state.get("glossary_terms", [])

    if issues or glossary_terms:
        # Has glossary terms → look them up first before refining
        if glossary_terms:
            return "glossary_lookup"
        # Has quality issues but no glossary terms → go straight to LLM
        return "refine_translation"

    # Clean translation
    return "passthrough"


def route_after_glossary(state: AgentState) -> str:
    """After glossary lookup, always go to LLM refinement."""
    return "refine_translation"