# evals/llm_judge.py
# Uses Sarvam 105B as an impartial judge to rate translation quality.
# LLM-as-judge is more nuanced than BLEU: it catches fluency, cultural appropriateness,
# and meaning preservation even when word choice differs from the reference.
# Score: 0.0 to 1.0 (judge returns 1–10, we normalize).

import httpx
import logging
import re
import json

logger = logging.getLogger(__name__)

SARVAM_LLM_BASE = "https://api.sarvam.ai"
SARVAM_LLM_MODEL = "sarvam-m"

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator of machine translation quality for Indian languages.
You will be given:
1. A source text in an Indian language
2. A reference (gold standard) translation
3. A hypothesis (machine-generated) translation

Score the hypothesis on two dimensions:
- Accuracy (0-10): Does it preserve the meaning of the source?
- Fluency (0-10): Does it sound natural in the target language?

Respond ONLY with valid JSON in this exact format:
{"accuracy": <int>, "fluency": <int>, "reasoning": "<one sentence>"}

No other text. No markdown. Just the JSON object."""


async def llm_judge_single(
    source_text: str,
    reference: str,
    hypothesis: str,
    source_lang: str,
    target_lang: str,
    api_key: str,
) -> dict:
    """
    Asks Sarvam 105B to score one translation.
    Returns:
        {
            "accuracy": 8,
            "fluency": 7,
            "combined_score": 0.75,   # (accuracy + fluency) / 20
            "reasoning": "..."
        }
    Falls back to {"accuracy": 0, "fluency": 0, "combined_score": 0.0} on failure.
    """
    user_prompt = (
        f"Source language: {source_lang}\n"
        f"Target language: {target_lang}\n\n"
        f"Source text: {source_text}\n\n"
        f"Reference translation: {reference}\n\n"
        f"Hypothesis translation: {hypothesis}\n\n"
        f"Rate the hypothesis translation."
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{SARVAM_LLM_BASE}/chat/completions",
                headers={"api-subscription-key": api_key},
                json={
                    "model": SARVAM_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.0,  # Zero temp for deterministic judgment
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()

            # Strip markdown fences if model adds them despite instructions
            content = re.sub(r"```json\s*|\s*```", "", content).strip()
            scores = json.loads(content)

            accuracy = int(scores.get("accuracy", 0))
            fluency = int(scores.get("fluency", 0))
            combined = round((accuracy + fluency) / 20.0, 4)  # normalize to 0–1

            return {
                "accuracy": accuracy,
                "fluency": fluency,
                "combined_score": combined,
                "reasoning": scores.get("reasoning", ""),
            }

    except json.JSONDecodeError as e:
        logger.warning(f"LLM judge returned invalid JSON: {e}")
        return {"accuracy": 0, "fluency": 0, "combined_score": 0.0, "reasoning": "parse_error"}
    except Exception as e:
        logger.error(f"LLM judge call failed: {e}")
        return {"accuracy": 0, "fluency": 0, "combined_score": 0.0, "reasoning": f"error: {e}"}


async def llm_judge_batch(
    cases: list[dict],
    api_key: str,
) -> dict:
    """
    Runs LLM judge on a list of eval cases.
    Each case must have: source_text, expected_translation, hypothesis, source_lang, target_lang.
    Returns aggregate stats.
    """
    import asyncio

    # Run all judge calls concurrently (but cap at 5 at a time to avoid rate limits)
    semaphore = asyncio.Semaphore(5)

    async def judged(case: dict) -> dict:
        async with semaphore:
            result = await llm_judge_single(
                source_text=case["source_text"],
                reference=case["expected_translation"],
                hypothesis=case["hypothesis"],
                source_lang=case["source_lang"],
                target_lang=case["target_lang"],
                api_key=api_key,
            )
            return {**case, "judge_scores": result}

    results = await asyncio.gather(*[judged(c) for c in cases])

    scores = [r["judge_scores"]["combined_score"] for r in results]
    mean_score = round(sum(scores) / len(scores), 4) if scores else 0.0

    return {
        "individual_results": results,
        "mean_llm_score": mean_score,
        "min_llm_score": round(min(scores), 4) if scores else 0.0,
        "max_llm_score": round(max(scores), 4) if scores else 0.0,
    }
