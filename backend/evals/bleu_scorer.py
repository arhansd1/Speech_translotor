# evals/bleu_scorer.py
# Computes BLEU score between predicted and reference translations.
# Uses sacrebleu — the standard for MT evaluation, produces reproducible scores.
# We use sentence-level BLEU averaged across all test cases, not corpus BLEU,
# because our test cases are short sentences and corpus BLEU underweights short refs.

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def compute_bleu(hypothesis: str, reference: str) -> float:
    """
    Computes sentence-level BLEU score between one hypothesis and one reference.
    Returns a float between 0.0 and 1.0.
    Returns 0.0 if sacrebleu is not installed or inputs are empty.
    """
    if not hypothesis.strip() or not reference.strip():
        return 0.0

    try:
        from sacrebleu.metrics import BLEU
        bleu = BLEU(effective_order=True)  # effective_order handles short sentences correctly
        score = bleu.sentence_score(hypothesis, [reference])
        # sacrebleu returns 0–100; normalize to 0–1
        return round(score.score / 100.0, 4)
    except ImportError:
        logger.warning("sacrebleu not installed — BLEU scoring disabled. Run: pip install sacrebleu")
        return 0.0
    except Exception as e:
        logger.error(f"BLEU computation failed: {e}")
        return 0.0


def compute_batch_bleu(pairs: list[dict]) -> dict:
    """
    Computes BLEU for a list of {"hypothesis": str, "reference": str} dicts.
    Returns:
        {
            "individual_scores": [0.85, 0.72, ...],
            "mean_bleu": 0.79,
            "min_bleu": 0.45,
            "max_bleu": 0.95
        }
    """
    if not pairs:
        return {"individual_scores": [], "mean_bleu": 0.0, "min_bleu": 0.0, "max_bleu": 0.0}

    scores = [compute_bleu(p["hypothesis"], p["reference"]) for p in pairs]
    return {
        "individual_scores": scores,
        "mean_bleu": round(sum(scores) / len(scores), 4),
        "min_bleu": round(min(scores), 4),
        "max_bleu": round(max(scores), 4),
    }
