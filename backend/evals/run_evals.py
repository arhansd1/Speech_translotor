# evals/run_evals.py
# Runs the full eval suite: 20 known Hindi→English pairs through the complete pipeline.
# Scoring: 40% BLEU + 60% LLM-as-judge (composite).
# This is what the /eval endpoint calls. Takes ~60–90s to complete.
# The final composite score is what you quote in the cover email.

import json
import time
import logging
import asyncio
from pathlib import Path
from typing import Optional

from sarvam.client import SarvamClient, SarvamError
from agent.graph import run_agent
from .bleu_scorer import compute_bleu, compute_batch_bleu
from .llm_judge import llm_judge_batch

logger = logging.getLogger(__name__)

# Where test cases live relative to this file
TEST_CASES_PATH = Path(__file__).parent / "test_cases.json"

# Scoring weights — must sum to 1.0
BLEU_WEIGHT = 0.40
LLM_WEIGHT = 0.60


def load_test_cases() -> list[dict]:
    with open(TEST_CASES_PATH) as f:
        return json.load(f)


async def run_single_case(
    case: dict,
    sarvam_client: SarvamClient,
    api_key: str,
) -> dict:
    """
    Runs ONE test case through the full agent pipeline using pre-existing
    translation (we skip live STT since test cases have known source text).
    In a real eval, you'd have recorded audio for each test case.
    Here we call Sarvam translate directly on the text, then run the agent.
    """
    start = time.time()

    try:
        # Step 1: Translate source text using Sarvam translate endpoint
        # (In prod this comes from the STT+Translate combined call)
        resp = await sarvam_client._client.post(
            "/translate",
            json={
                "input": case["source_text"],
                "source_language_code": case["source_lang"],
                "target_language_code": case["target_lang"],
                "model": "mayura:v1",
                "enable_preprocessing": True,
            },
        )
        if resp.status_code >= 400:
            raise SarvamError(f"Translate failed: {resp.text}", resp.status_code)

        raw_translation = resp.json().get("translated_text", "")

        # Step 2: Run through agent (quality check, glossary, optional LLM refinement)
        agent_result = await run_agent(
            raw_translation=raw_translation,
            transcript=case["source_text"],
            source_language=case["source_lang"],
            target_language=case["target_lang"],
            session_context="",  # No session context for isolated eval cases
            api_key=api_key,
        )

        hypothesis = agent_result["final_translation"]

        # Step 3: Compute BLEU immediately (fast, no API call)
        bleu = compute_bleu(hypothesis, case["expected_translation"])

        elapsed = round(time.time() - start, 2)

        return {
            "id": case["id"],
            "source_text": case["source_text"],
            "expected_translation": case["expected_translation"],
            "raw_sarvam_translation": raw_translation,
            "hypothesis": hypothesis,           # agent-refined output
            "agent_reasoning": agent_result.get("agent_reasoning", ""),
            "glossary_used": agent_result.get("glossary_used", False),
            "bleu_score": bleu,
            "domain": case["domain"],
            "latency_seconds": elapsed,
            "status": "ok",
        }

    except Exception as e:
        logger.error(f"Eval case {case['id']} failed: {e}")
        return {
            "id": case["id"],
            "source_text": case["source_text"],
            "expected_translation": case["expected_translation"],
            "hypothesis": "",
            "bleu_score": 0.0,
            "domain": case["domain"],
            "latency_seconds": 0.0,
            "status": "error",
            "error": str(e),
        }


async def run_full_eval(api_key: str) -> dict:
    """
    Main entry point called by the /eval route.
    Runs all 20 test cases, computes BLEU + LLM judge, returns composite score.
    """
    logger.info("Starting eval suite")
    suite_start = time.time()

    test_cases = load_test_cases()

    async with SarvamClient(api_key) as client:
        # Run cases with limited concurrency (3 at a time) to avoid rate limits
        semaphore = asyncio.Semaphore(3)

        async def bounded(case):
            async with semaphore:
                return await run_single_case(case, client, api_key)

        case_results = await asyncio.gather(*[bounded(c) for c in test_cases])

    # ── BLEU aggregate ──────────────────────────────────────────────────────
    bleu_pairs = [
        {"hypothesis": r["hypothesis"], "reference": r["expected_translation"]}
        for r in case_results if r["status"] == "ok"
    ]
    bleu_stats = compute_batch_bleu(bleu_pairs)

    # ── LLM judge ───────────────────────────────────────────────────────────
    judge_cases = [r for r in case_results if r["status"] == "ok"]
    llm_stats = await llm_judge_batch(judge_cases, api_key)

    # ── Composite score ──────────────────────────────────────────────────────
    mean_bleu = bleu_stats["mean_bleu"]
    mean_llm = llm_stats["mean_llm_score"]
    composite = round(BLEU_WEIGHT * mean_bleu + LLM_WEIGHT * mean_llm, 4)
    composite_pct = round(composite * 100, 1)  # e.g. 87.3

    # ── Domain breakdown ────────────────────────────────────────────────────
    domain_scores: dict[str, list[float]] = {}
    for r in case_results:
        if r["status"] == "ok":
            d = r["domain"]
            domain_scores.setdefault(d, []).append(r["bleu_score"])
    domain_avg = {
        d: round(sum(scores) / len(scores), 4)
        for d, scores in domain_scores.items()
    }

    total_time = round(time.time() - suite_start, 1)
    passed = sum(1 for r in case_results if r["status"] == "ok")

    result = {
        "summary": {
            "composite_score": composite,
            "composite_score_pct": composite_pct,   # Quote this in the cover email!
            "mean_bleu": mean_bleu,
            "mean_llm_score": mean_llm,
            "bleu_weight": BLEU_WEIGHT,
            "llm_weight": LLM_WEIGHT,
            "cases_passed": passed,
            "cases_failed": len(case_results) - passed,
            "total_cases": len(test_cases),
            "total_time_seconds": total_time,
        },
        "domain_bleu_scores": domain_avg,
        "bleu_stats": bleu_stats,
        "llm_stats": {
            "mean_llm_score": llm_stats["mean_llm_score"],
            "min_llm_score": llm_stats["min_llm_score"],
            "max_llm_score": llm_stats["max_llm_score"],
        },
        "case_results": case_results,
    }

    logger.info(
        f"Eval complete: composite={composite_pct}% "
        f"(BLEU={mean_bleu:.3f}, LLM={mean_llm:.3f}) "
        f"in {total_time}s"
    )
    return result
